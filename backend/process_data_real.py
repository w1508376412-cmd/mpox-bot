"""
数据处理模块 - 将 data/raw 原始文本切分、向量化并写入数据库。

该脚本使用轻量工程化预处理链路：
1. 统一解析原始文件元数据
2. 做基础质量检查
3. 使用配置化切片参数
4. 同时写入 pgvector 的 embedding 列和兼容用 embedding_json
5. 使用 checkpoint 支持断点续跑
6. 生成每次运行的 JSON 报告
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import json

import psycopg

from checkpoint_manager import CheckpointManager
from config import get_settings
from embedder_alibaba import embed_batch
from pipeline_config import PIPELINE_CONFIG
from preprocess_utils import (
    chunk_document,
    create_chunk_records,
    is_superseded_raw_file,
    parse_raw_file,
    validate_document,
)


settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding="utf8",
    )


def ensure_enhanced_schema(cur) -> None:
    """Add quality/provenance columns when rebuilding an older local database."""
    statements = [
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_primary TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_department TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_orgs TEXT[]",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS url_status TEXT DEFAULT 'present'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS url_missing_reason TEXT DEFAULT ''",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS date_source TEXT DEFAULT 'raw_publish_date'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS date_confidence TEXT DEFAULT 'high'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS original_file TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS content_preview TEXT",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS content_hash TEXT",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS section_title TEXT",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS chunk_index INTEGER",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS start_char INTEGER",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS end_char INTEGER",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_json JSONB",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_model TEXT DEFAULT 'text-embedding-v4'",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS source_primary TEXT",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS source_department TEXT",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS date_confidence TEXT DEFAULT 'high'",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 2",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS quality_score NUMERIC(3,2) DEFAULT 1.00",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS quality_warnings TEXT[] DEFAULT '{}'",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS contains_mpox_keyword BOOLEAN DEFAULT true",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS is_footer_like BOOLEAN DEFAULT false",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS is_suspected_irrelevant BOOLEAN DEFAULT false",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'zh'",
        "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "CREATE INDEX IF NOT EXISTS chunks_content_hash_idx ON chunks(content_hash)",
        "CREATE INDEX IF NOT EXISTS chunks_quality_score_idx ON chunks(quality_score)",
    ]
    for statement in statements:
        cur.execute(statement)


def collect_raw_files(raw_dir: str | Path) -> List[Path]:
    """收集所有待处理的 raw txt 文件。"""
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        return []
    return sorted(
        path
        for path in raw_path.rglob("*.txt")
        if path.is_file() and not path.name.startswith("~$") and not is_superseded_raw_file(path)
    )


def upsert_document(cur, metadata: Dict[str, Any]) -> None:
    """写入或更新 documents 表，保证 chunks 的外键可用。"""
    cur.execute(
        """
        INSERT INTO documents
        (id, title, source, source_primary, source_department, source_orgs, url,
         url_status, url_missing_reason, publish_date, date_source, date_confidence,
         region, original_file, processed_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            source = EXCLUDED.source,
            source_primary = EXCLUDED.source_primary,
            source_department = EXCLUDED.source_department,
            source_orgs = EXCLUDED.source_orgs,
            url = EXCLUDED.url,
            url_status = EXCLUDED.url_status,
            url_missing_reason = EXCLUDED.url_missing_reason,
            publish_date = EXCLUDED.publish_date,
            date_source = EXCLUDED.date_source,
            date_confidence = EXCLUDED.date_confidence,
            region = EXCLUDED.region,
            original_file = EXCLUDED.original_file,
            processed_at = EXCLUDED.processed_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            metadata.get("document_id"),
            metadata.get("title", "unknown"),
            metadata.get("source", "Unknown"),
            metadata.get("source_primary", metadata.get("source", "Unknown")),
            metadata.get("source_department", ""),
            metadata.get("source_orgs", [metadata.get("source", "Unknown")]),
            metadata.get("url", ""),
            metadata.get("url_status", "present" if metadata.get("url") else "missing"),
            metadata.get("url_missing_reason", ""),
            metadata.get("publish_date"),
            metadata.get("date_source", "raw_publish_date"),
            metadata.get("date_confidence", "high"),
            metadata.get("region", "global"),
            metadata.get("original_file", ""),
        ),
    )


def supports_pgvector(cur) -> bool:
    """Return whether the current chunks table has a pgvector embedding column."""
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'chunks'
              AND column_name = 'embedding'
        )
        """
    )
    return bool(cur.fetchone()[0])


def upsert_chunks(
    cur,
    chunk_records: List[Dict[str, Any]],
    embeddings: List[List[float]],
    use_pgvector: bool,
) -> None:
    """写入或更新 chunks 表。"""
    for chunk_record, embedding in zip(chunk_records, embeddings):
        metadata = chunk_record["metadata"]
        quality = chunk_record["quality"]
        embedding_json = json.dumps(embedding)
        if use_pgvector:
            cur.execute(
                """
                INSERT INTO chunks
                (id, document_id, content, content_preview, content_hash, section_title,
                 chunk_index, start_char, end_char, topic,
                 source, source_primary, source_department, url, publish_date, date_confidence,
                 region, priority, embedding, embedding_json, embedding_model,
                 quality_score, quality_warnings, contains_mpox_keyword, is_footer_like,
                 is_suspected_irrelevant, language, processed_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::vector, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, true)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    content_preview = EXCLUDED.content_preview,
                    content_hash = EXCLUDED.content_hash,
                    section_title = EXCLUDED.section_title,
                    chunk_index = EXCLUDED.chunk_index,
                    start_char = EXCLUDED.start_char,
                    end_char = EXCLUDED.end_char,
                    topic = EXCLUDED.topic,
                    embedding = EXCLUDED.embedding,
                    embedding_json = EXCLUDED.embedding_json,
                    embedding_model = EXCLUDED.embedding_model,
                    source = EXCLUDED.source,
                    source_primary = EXCLUDED.source_primary,
                    source_department = EXCLUDED.source_department,
                    url = EXCLUDED.url,
                    publish_date = EXCLUDED.publish_date,
                    date_confidence = EXCLUDED.date_confidence,
                    region = EXCLUDED.region,
                    priority = EXCLUDED.priority,
                    quality_score = EXCLUDED.quality_score,
                    quality_warnings = EXCLUDED.quality_warnings,
                    contains_mpox_keyword = EXCLUDED.contains_mpox_keyword,
                    is_footer_like = EXCLUDED.is_footer_like,
                    is_suspected_irrelevant = EXCLUDED.is_suspected_irrelevant,
                    language = EXCLUDED.language,
                    processed_at = EXCLUDED.processed_at,
                    is_active = true
                """,
                (
                    chunk_record["id"],
                    chunk_record["document_id"],
                    chunk_record["content"],
                    chunk_record["content_preview"],
                    chunk_record["content_hash"],
                    chunk_record["section_title"],
                    chunk_record["chunk_index"],
                    chunk_record["start_char"],
                    chunk_record["end_char"],
                    metadata.get("topic", []),
                    metadata.get("source", "Unknown"),
                    metadata.get("source_primary", metadata.get("source", "Unknown")),
                    metadata.get("source_department", ""),
                    metadata.get("url", ""),
                    metadata.get("publish_date"),
                    metadata.get("date_confidence", "high"),
                    metadata.get("region", "global"),
                    metadata.get("priority", 2),
                    embedding,
                    embedding_json,
                    settings.embedding_model,
                    quality["quality_score"],
                    quality["quality_warnings"],
                    quality["contains_mpox_keyword"],
                    quality["is_footer_like"],
                    quality["is_suspected_irrelevant"],
                    quality["language"],
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO chunks
                (id, document_id, content, content_preview, content_hash, section_title,
                 chunk_index, start_char, end_char, topic,
                 source, source_primary, source_department, url, publish_date, date_confidence,
                 region, priority, embedding_json, embedding_model,
                 quality_score, quality_warnings, contains_mpox_keyword, is_footer_like,
                 is_suspected_irrelevant, language, processed_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, true)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    content_preview = EXCLUDED.content_preview,
                    content_hash = EXCLUDED.content_hash,
                    section_title = EXCLUDED.section_title,
                    chunk_index = EXCLUDED.chunk_index,
                    start_char = EXCLUDED.start_char,
                    end_char = EXCLUDED.end_char,
                    topic = EXCLUDED.topic,
                    embedding_json = EXCLUDED.embedding_json,
                    embedding_model = EXCLUDED.embedding_model,
                    source = EXCLUDED.source,
                    source_primary = EXCLUDED.source_primary,
                    source_department = EXCLUDED.source_department,
                    url = EXCLUDED.url,
                    publish_date = EXCLUDED.publish_date,
                    date_confidence = EXCLUDED.date_confidence,
                    region = EXCLUDED.region,
                    priority = EXCLUDED.priority,
                    quality_score = EXCLUDED.quality_score,
                    quality_warnings = EXCLUDED.quality_warnings,
                    contains_mpox_keyword = EXCLUDED.contains_mpox_keyword,
                    is_footer_like = EXCLUDED.is_footer_like,
                    is_suspected_irrelevant = EXCLUDED.is_suspected_irrelevant,
                    language = EXCLUDED.language,
                    processed_at = EXCLUDED.processed_at,
                    is_active = true
                """,
                (
                    chunk_record["id"],
                    chunk_record["document_id"],
                    chunk_record["content"],
                    chunk_record["content_preview"],
                    chunk_record["content_hash"],
                    chunk_record["section_title"],
                    chunk_record["chunk_index"],
                    chunk_record["start_char"],
                    chunk_record["end_char"],
                    metadata.get("topic", []),
                    metadata.get("source", "Unknown"),
                    metadata.get("source_primary", metadata.get("source", "Unknown")),
                    metadata.get("source_department", ""),
                    metadata.get("url", ""),
                    metadata.get("publish_date"),
                    metadata.get("date_confidence", "high"),
                    metadata.get("region", "global"),
                    metadata.get("priority", 2),
                    embedding_json,
                    settings.embedding_model,
                    quality["quality_score"],
                    quality["quality_warnings"],
                    quality["contains_mpox_keyword"],
                    quality["is_footer_like"],
                    quality["is_suspected_irrelevant"],
                    quality["language"],
                ),
            )


def save_report(report: Dict[str, Any]) -> Path:
    """保存本次处理报告。"""
    PIPELINE_CONFIG.report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = PIPELINE_CONFIG.report_dir / f"preprocess_report_{timestamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def process_one_file(file_path: Path, conn) -> Dict[str, Any]:
    """处理单个 raw 文件。"""
    parsed = parse_raw_file(file_path)
    quality = validate_document(parsed.metadata, parsed.content)

    if not quality.passed:
        return {
            "file": str(file_path),
            "success": False,
            "error": "quality_check_failed",
            "quality": quality.__dict__,
        }

    chunks = chunk_document(parsed.content)
    chunk_records = create_chunk_records(parsed.metadata, chunks)
    if not chunk_records:
        return {
            "file": str(file_path),
            "success": False,
            "error": "no_chunks_generated",
            "quality": quality.__dict__,
        }

    embeddings = embed_batch(
        [chunk["content"] for chunk in chunk_records],
        batch_size=PIPELINE_CONFIG.embedding_batch_size,
    )

    with conn.cursor() as cur:
        ensure_enhanced_schema(cur)
        use_pgvector = supports_pgvector(cur)
        upsert_document(cur, parsed.metadata)
        upsert_chunks(cur, chunk_records, embeddings, use_pgvector)

    conn.commit()

    return {
        "file": str(file_path),
        "success": True,
        "source": parsed.metadata.get("source"),
        "title": parsed.metadata.get("title"),
        "priority": parsed.metadata.get("priority"),
        "content_length": len(parsed.content),
        "chunks": len(chunk_records),
        "quality": quality.__dict__,
    }


def process_all_raw_files(raw_dir: str = "data/raw"):
    """
    处理所有原始数据文件。

    Args:
        raw_dir: 原始数据目录
    """
    print("=" * 80)
    print("开始处理原始数据并生成向量")
    print("=" * 80)

    checkpoint = CheckpointManager(PIPELINE_CONFIG.checkpoint_path)
    all_files = collect_raw_files(raw_dir)

    report: Dict[str, Any] = {
        "started_at": datetime.now().isoformat(),
        "raw_dir": str(raw_dir),
        "total_files_found": len(all_files),
        "processed": [],
        "skipped": [],
        "failed": [],
    }

    print(f"\n找到 {len(all_files)} 个原始数据文件")

    conn = get_db_connection()
    try:
        for file_path in all_files:
            if checkpoint.is_processed(file_path):
                print(f"跳过已处理文件: {file_path.name}")
                report["skipped"].append(str(file_path))
                continue

            print(f"\n处理: {file_path.name}")
            try:
                result = process_one_file(file_path, conn)
                if result["success"]:
                    checkpoint.record_success(
                        file_path,
                        {
                            "chunks": result["chunks"],
                            "quality_score": result["quality"]["score"],
                            "title": result["title"],
                        },
                    )
                    report["processed"].append(result)
                    print(f"  ✓ 写入 {result['chunks']} 个知识片段")
                else:
                    conn.rollback()
                    checkpoint.record_failure(file_path, result["error"], result)
                    report["failed"].append(result)
                    print(f"  ⚠️  跳过: {result['error']}")

            except Exception as exc:
                conn.rollback()
                error_result = {
                    "file": str(file_path),
                    "success": False,
                    "error": str(exc),
                }
                checkpoint.record_failure(file_path, str(exc), error_result)
                report["failed"].append(error_result)
                print(f"  ❌ 处理失败: {exc}")

    finally:
        conn.close()

    report["finished_at"] = datetime.now().isoformat()
    report["summary"] = {
        "processed_files": len(report["processed"]),
        "skipped_files": len(report["skipped"]),
        "failed_files": len(report["failed"]),
        "chunks_written": sum(item.get("chunks", 0) for item in report["processed"]),
        "checkpoint": checkpoint.get_summary(),
    }
    report_path = save_report(report)

    print("\n" + "=" * 80)
    print("数据处理完成！")
    print(f"处理文件: {report['summary']['processed_files']}")
    print(f"跳过文件: {report['summary']['skipped_files']}")
    print(f"失败文件: {report['summary']['failed_files']}")
    print(f"写入片段: {report['summary']['chunks_written']}")
    print(f"报告路径: {report_path}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    print("猴痘知识库数据处理工具")
    print("将原始数据切分并生成向量\n")

    try:
        process_all_raw_files()
    except Exception as e:
        print(f"\n处理失败: {e}")
        exit(1)
