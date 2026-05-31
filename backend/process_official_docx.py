"""
读取并处理docx文件
"""
from docx import Document
import os
import json
import psycopg
import uuid
from datetime import date
from embedder_alibaba import embed_batch
from config import get_settings

settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding='utf8'
    )


def read_docx(file_path: str) -> str:
    """读取docx文件内容"""
    try:
        doc = Document(file_path)
        full_text = []

        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)

        return '\n'.join(full_text)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80):
    """将长文本切分成小片段"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if end < len(text):
            last_period = chunk.rfind('。')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)

            if break_point > chunk_size * 0.5:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if len(c) > 50]


def process_docx_files(file_configs):
    """处理docx文件并保存到数据库"""
    print("="*80)
    print("处理官方docx文件")
    print("="*80)

    conn = get_db_connection()
    all_chunk_data = []

    try:
        for config in file_configs:
            print(f"\n处理: {config['title']}")
            print(f"  来源: {config['source']}")
            print(f"  文件: {config['file_path']}")

            # 读取docx内容
            content = read_docx(config['file_path'])

            if not content:
                print(f"  ⚠️  无法读取文件内容")
                continue

            print(f"  ✓ 读取成功: {len(content)} 字符")

            # 保存原始内容
            output_dir = f"data/raw/{config['source']}"
            os.makedirs(output_dir, exist_ok=True)

            output_file = f"{output_dir}/{config['id']}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"来源：{config['source']}\n")
                f.write(f"标题：{config['title']}\n")
                f.write(f"URL：{config['url']}\n")
                f.write(f"发布日期：{config['publish_date']}\n")
                f.write(f"地区：{config['region']}\n")
                f.write(f"优先级：{config['priority']}\n")
                f.write(f"主题：{', '.join(config['topic'])}\n")
                f.write("\n" + "="*80 + "\n\n")
                f.write(content)

            print(f"  ✓ 已保存原始文件: {output_file}")

            # 切分文本
            chunks = chunk_text(content, chunk_size=600, overlap=80)
            print(f"  ✓ 切分成 {len(chunks)} 个片段")

            # 保存片段信息
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                all_chunk_data.append({
                    'id': chunk_id,
                    'content': chunk,
                    'metadata': config
                })

        total_chunks = len(all_chunk_data)
        print(f"\n总共生成 {total_chunks} 个知识片段")

        # 批量生成向量
        print(f"\n正在生成向量...")
        contents = [chunk['content'] for chunk in all_chunk_data]
        embeddings = embed_batch(contents, batch_size=10)

        # 保存到数据库
        print(f"\n正在保存到数据库...")

        with conn.cursor() as cur:
            for chunk_data, embedding in zip(all_chunk_data, embeddings):
                metadata = chunk_data['metadata']
                embedding_json = json.dumps(embedding)

                cur.execute(
                    """
                    INSERT INTO chunks
                    (id, document_id, content, topic, source, url, publish_date, region, priority, embedding, embedding_json, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb, true)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        embedding_json = EXCLUDED.embedding_json,
                        priority = EXCLUDED.priority
                    """,
                    (
                        chunk_data['id'],
                        metadata['title'],
                        chunk_data['content'],
                        metadata['topic'],
                        metadata['source'],
                        metadata['url'],
                        metadata['publish_date'],
                        metadata['region'],
                        metadata['priority'],
                        embedding,
                        embedding_json
                    )
                )

        conn.commit()

        print(f"\n✓ 成功保存 {total_chunks} 个知识片段到数据库")

        # 验证结果
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
    print("处理完成！")
    print("="*80)


if __name__ == "__main__":
    # 配置两个官方文件
    file_configs = [
        {
            "id": "ndcpa_mpox_prevention_plan_2023",
            "file_path": "/Users/yanfei/Desktop/猴痘防控方案.docx",
            "title": "猴痘防控方案",
            "source": "国家疾控局",
            "url": "https://www.ndcpa.gov.cn/jbkzzx/c100014/common/content/content_1698984403881291776.html",
            "region": "中国",
            "priority": 1,
            "topic": ["防控方案", "政策", "就医指导", "疫情监测", "流行病学调查"],
            "publish_date": date(2023, 7, 26)
        },
        {
            "id": "nhc_mpox_technical_guide_2022",
            "file_path": "/Users/yanfei/Desktop/猴痘防控技术指南(2022年版).docx",
            "title": "猴痘防控技术指南（2022年版）",
            "source": "国家卫健委",
            "url": "https://www.nhc.gov.cn/yjb/c100058/202207/fdaf10006d0b4034bca46a28b5f0bd20.shtml",
            "region": "中国",
            "priority": 1,
            "topic": ["技术指南", "防控", "诊断", "治疗", "隔离", "密接管理"],
            "publish_date": date(2022, 7, 1)
        }
    ]

    print("国家疾控局和国家卫健委官方文件处理工具\n")
    process_docx_files(file_configs)
