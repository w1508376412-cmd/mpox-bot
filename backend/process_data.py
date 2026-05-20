"""数据处理脚本 - 将抓取的文档处理成向量并存入数据库"""
import os
import sys
import json
from datetime import date
import psycopg
from crawler import SOURCES, fetch_page
from chunker import process_document
from embedder import embed_batch
from config import get_settings

settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(settings.database_url)


def insert_document(conn, metadata: dict):
    """插入文档元数据"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (id, title, source, url, publish_date, region)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                publish_date = EXCLUDED.publish_date,
                region = EXCLUDED.region,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                metadata["id"],
                metadata["title"],
                metadata["source"],
                metadata["url"],
                metadata["publish_date"],
                metadata["region"]
            )
        )
    conn.commit()


def insert_chunks(conn, chunks: list):
    """批量插入知识片段"""
    # 提取所有内容用于生成向量
    contents = [chunk["content"] for chunk in chunks]

    print(f"正在生成 {len(contents)} 个向量...")
    embeddings = embed_batch(contents)

    print("正在插入数据库...")
    with conn.cursor() as cur:
        for chunk, embedding in zip(chunks, embeddings):
            # 根据来源设置优先级
            source = chunk["source"]
            if "中国疾控" in source or "卫健委" in source:
                priority = 1
            elif source in ["WHO", "CDC", "ECDC"]:
                priority = 2
            else:
                priority = 3

            cur.execute(
                """
                INSERT INTO chunks
                (id, document_id, content, topic, embedding, source, url, publish_date, region, priority, embedding_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    topic = EXCLUDED.topic,
                    embedding = EXCLUDED.embedding,
                    source = EXCLUDED.source,
                    url = EXCLUDED.url,
                    publish_date = EXCLUDED.publish_date,
                    region = EXCLUDED.region,
                    priority = EXCLUDED.priority,
                    embedding_json = EXCLUDED.embedding_json
                """,
                (
                    chunk["id"],
                    chunk["document_id"],
                    chunk["content"],
                    chunk["topic"],
                    embedding,
                    chunk["source"],
                    chunk["url"],
                    chunk["publish_date"],
                    chunk["region"],
                    priority,
                    json.dumps(embedding)  # 同时保存到embedding_json以保持兼容性
                )
            )
    conn.commit()


def process_all_sources():
    """处理所有数据源"""
    conn = get_db_connection()

    try:
        for source_config in SOURCES:
            print(f"\n{'='*60}")
            print(f"处理: {source_config['title']}")
            print(f"{'='*60}")

            # 读取原始文本
            source_dir = source_config["source"].lower().replace(" ", "_")
            file_path = f"data/raw/{source_dir}/{source_config['id']}.txt"

            if not os.path.exists(file_path):
                print(f"⚠️  文件不存在: {file_path}")
                print("正在抓取...")
                content = fetch_page(source_config["url"])
                if not content:
                    print("抓取失败，跳过")
                    continue
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

            if not text.strip():
                print("⚠️  文件为空，跳过")
                continue

            # 插入文档元数据
            print("插入文档元数据...")
            insert_document(conn, source_config)

            # 处理文档，生成片段
            print("切分文档...")
            chunks = process_document(text, source_config)
            print(f"生成了 {len(chunks)} 个片段")

            # 插入片段和向量
            insert_chunks(conn, chunks)

            print(f"✓ 完成: {source_config['title']}")

        print(f"\n{'='*60}")
        print("所有文档处理完成！")
        print(f"{'='*60}")

    finally:
        conn.close()


if __name__ == "__main__":
    print("猴痘知识库数据处理")
    print("="*60)

    # 检查环境变量
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        print("❌ 错误: 请先配置 OPENAI_API_KEY")
        print("请复制 .env.example 为 .env 并填入您的 API key")
        sys.exit(1)

    try:
        process_all_sources()
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        sys.exit(1)
