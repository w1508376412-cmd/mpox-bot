"""
数据处理模块 - 将抓取的原始数据切分并生成向量
"""
import os
import psycopg
import json
from datetime import date
from typing import List, Dict
from embedder_alibaba import embed_batch
from config import get_settings
import uuid

settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding='utf8'
    )


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> List[str]:
    """
    将长文本切分成小片段

    Args:
        text: 输入文本
        chunk_size: 片段大小（字符数）
        overlap: 重叠大小（字符数）

    Returns:
        文本片段列表
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # 如果不是最后一个片段，尝试在句号处断开
        if end < len(text):
            last_period = chunk.rfind('。')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > chunk_size * 0.5:  # 至少保留一半内容
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if len(c) > 50]  # 过滤太短的片段


def parse_raw_file(file_path: str) -> Dict:
    """
    解析原始数据文件

    Args:
        file_path: 文件路径

    Returns:
        包含元数据和内容的字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析元数据
    lines = content.split('\n')
    metadata = {}
    content_start = 0

    for i, line in enumerate(lines):
        if line.startswith('来源：'):
            metadata['source'] = line.replace('来源：', '').strip()
        elif line.startswith('标题：'):
            metadata['title'] = line.replace('标题：', '').strip()
        elif line.startswith('URL：'):
            metadata['url'] = line.replace('URL：', '').strip()
        elif line.startswith('发布日期：'):
            date_str = line.replace('发布日期：', '').strip()
            metadata['publish_date'] = date_str
        elif line.startswith('地区：'):
            metadata['region'] = line.replace('地区：', '').strip()
        elif line.startswith('优先级：'):
            metadata['priority'] = int(line.replace('优先级：', '').strip())
        elif line.startswith('主题：'):
            topics = line.replace('主题：', '').strip()
            metadata['topic'] = [t.strip() for t in topics.split(',')]
        elif '=' * 50 in line:
            content_start = i + 1
            break

    # 提取正文
    main_content = '\n'.join(lines[content_start:]).strip()

    return {
        'metadata': metadata,
        'content': main_content
    }


def process_all_raw_files(raw_dir: str = "data/raw"):
    """
    处理所有原始数据文件

    Args:
        raw_dir: 原始数据目录
    """
    print("="*80)
    print("开始处理原始数据并生成向量")
    print("="*80)

    conn = get_db_connection()

    try:
        # 1. 收集所有原始文件
        all_files = []
        for root, dirs, files in os.walk(raw_dir):
            for file in files:
                if file.endswith('.txt'):
                    all_files.append(os.path.join(root, file))

        print(f"\n找到 {len(all_files)} 个原始数据文件")

        # 2. 处理每个文件
        total_chunks = 0
        all_chunk_data = []

        for file_path in all_files:
            print(f"\n处理: {os.path.basename(file_path)}")

            # 解析文件
            parsed = parse_raw_file(file_path)
            metadata = parsed['metadata']
            content = parsed['content']

            print(f"  来源: {metadata.get('source', 'Unknown')}")
            print(f"  优先级: {metadata.get('priority', 2)}")
            print(f"  内容长度: {len(content)} 字符")

            # 切分文本
            chunks = chunk_text(content, chunk_size=600, overlap=80)
            print(f"  切分成 {len(chunks)} 个片段")

            # 保存片段信息
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                all_chunk_data.append({
                    'id': chunk_id,
                    'content': chunk,
                    'metadata': metadata
                })

            total_chunks += len(chunks)

        print(f"\n总共生成 {total_chunks} 个知识片段")

        # 3. 批量生成向量
        print(f"\n正在生成向量...")
        contents = [chunk['content'] for chunk in all_chunk_data]
        embeddings = embed_batch(contents, batch_size=10)  # 阿里百炼限制最多10个

        # 4. 保存到数据库
        print(f"\n正在保存到数据库...")

        with conn.cursor() as cur:
            for chunk_data, embedding in zip(all_chunk_data, embeddings):
                metadata = chunk_data['metadata']
                embedding_json = json.dumps(embedding)

                # 插入chunks表
                cur.execute(
                    """
                    INSERT INTO chunks
                    (id, document_id, content, topic, source, url, publish_date, region, priority, embedding_json, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, true)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding_json = EXCLUDED.embedding_json,
                        priority = EXCLUDED.priority
                    """,
                    (
                        chunk_data['id'],
                        metadata.get('title', 'unknown'),  # document_id
                        chunk_data['content'],
                        metadata.get('topic', []),
                        metadata.get('source', 'Unknown'),
                        metadata.get('url', ''),
                        metadata.get('publish_date', date.today()),
                        metadata.get('region', 'global'),
                        metadata.get('priority', 2),
                        embedding_json
                    )
                )

        conn.commit()

        print(f"\n✓ 成功保存 {total_chunks} 个知识片段到数据库")

        # 5. 验证结果
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    priority,
                    CASE priority
                        WHEN 1 THEN '国内口径'
                        WHEN 2 THEN '国际基准'
                        WHEN 3 THEN '区域疫情'
                    END as priority_name,
                    COUNT(*) as count,
                    COUNT(embedding_json) as with_vector
                FROM chunks
                WHERE is_active = true
                GROUP BY priority
                ORDER BY priority
                """
            )

            results = cur.fetchall()

            print(f"\n数据统计（按优先级）:")
            print(f"{'优先级':<15} {'片段数':<10} {'向量数':<10}")
            print("-" * 40)

            total_count = 0
            total_vector = 0

            for row in results:
                priority, priority_name, count, with_vector = row
                print(f"{priority_name:<15} {count:<10} {with_vector:<10}")
                total_count += count
                total_vector += with_vector

            print("-" * 40)
            print(f"{'总计':<15} {total_count:<10} {total_vector:<10}")
            print(f"\n向量覆盖率: {total_vector/total_count*100:.1f}%")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n" + "="*80)
    print("数据处理完成！")
    print("="*80)


if __name__ == "__main__":
    print("猴痘知识库数据处理工具")
    print("将原始数据切分并生成向量\n")

    try:
        process_all_raw_files()
    except Exception as e:
        print(f"\n处理失败: {e}")
        exit(1)
