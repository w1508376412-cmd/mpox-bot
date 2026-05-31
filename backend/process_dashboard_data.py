import os
import sys
import json
import uuid
import psycopg
from datetime import date
from typing import List

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler_shiny import scrape_who_dashboard
from embedder_alibaba import embed_batch
from config import get_settings

settings = get_settings()

def get_db_connection():
    return psycopg.connect(settings.database_url, client_encoding='utf8')

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if end < len(text):
            last_period = chunk.rfind('。')
            if last_period == -1: last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size * 0.4:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if len(c) > 30]

def process_and_update():
    print("=" * 60)
    print("开始执行每日数据更新任务")
    print("=" * 60)
    
    try:
        # 1. 抓取动态数据
        content = scrape_who_dashboard()
        if not content:
            print("❌ 抓取内容为空，停止更新")
            return

        # 2. 准备 Metadata
        metadata = {
            'id': 'who_dashboard_live',
            'source': 'WHO Mpox Global Dashboard',
            'title': 'WHO Mpox Global Dashboard (Live Stats)',
            'url': 'https://worldhealthorg.shinyapps.io/mpx_global/',
            'publish_date': date.today(),
            'region': 'global',
            'priority': 1,
            'topic': ['epidemiology', 'real-time stats']
        }

        # 3. 切分与生成向量
        print("正在处理文本并生成向量...")
        chunks = chunk_text(content)
        embeddings = embed_batch(chunks, batch_size=10)

        # 4. 更新数据库 (UPSERT)
        # 我们使用一个固定的 document_id 来标记仪表盘数据，每次运行都覆盖旧的
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 首先将旧的仪表盘片段标为不活跃 (或者直接删除，取决于策略)
                # 这里我们选择直接删除该 source 的旧记录，以保持数据库整洁
                cur.execute(
                    "DELETE FROM chunks WHERE source = %s",
                    (metadata['source'],)
                )
                
                print(f"正在保存 {len(chunks)} 个新知识片段...")
                for text, embedding in zip(chunks, embeddings):
                    chunk_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO chunks
                        (id, document_id, content, topic, source, url, publish_date, region, priority, embedding, embedding_json, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb, true)
                        """,
                        (
                            chunk_id,
                            metadata['id'],
                            text,
                            metadata['topic'],
                            metadata['source'],
                            metadata['url'],
                            metadata['publish_date'],
                            metadata['region'],
                            metadata['priority'],
                            embedding,
                            json.dumps(embedding)
                        )
                    )
            conn.commit()
            print(f"✓ 成功完成更新！已存入 {len(chunks)} 条最新记录。")
        except Exception as e:
            print(f"❌ 数据库操作失败: {e}")
            conn.rollback()
        finally:
            conn.close()

    except Exception as e:
        print(f"❌ 更新任务执行出错: {e}")

if __name__ == "__main__":
    process_and_update()
