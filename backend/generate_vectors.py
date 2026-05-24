"""
为现有数据生成向量
使用阿里百炼API生成embedding并存入数据库
"""
import psycopg
import json
from embedder_alibaba import embed_batch
from config import get_settings

settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding='utf8'
    )


def generate_vectors_for_existing_data():
    """为数据库中现有的知识片段生成向量"""

    print("="*60)
    print("开始为现有数据生成向量")
    print("="*60)

    conn = get_db_connection()

    try:
        # 1. 获取所有没有向量的片段
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content
                FROM chunks
                WHERE is_active = true
                  AND (embedding_json IS NULL OR embedding_json::text = 'null')
                ORDER BY id
                """
            )

            rows = cur.fetchall()

            if not rows:
                print("✓ 所有片段都已有向量，无需处理")
                return

            print(f"找到 {len(rows)} 个需要生成向量的片段")

            # 2. 提取ID和内容
            chunk_ids = [row[0] for row in rows]
            contents = [row[1] for row in rows]

            # 3. 批量生成向量
            print("\n正在生成向量...")
            embeddings = embed_batch(contents, batch_size=10)

            # 4. 更新数据库
            print("\n正在更新数据库...")
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                embedding_json = json.dumps(embedding)

                cur.execute(
                    """
                    UPDATE chunks
                    SET embedding = %s::vector,
                        embedding_json = %s::jsonb
                    WHERE id = %s
                    """,
                    (embedding, embedding_json, chunk_id)
                )

            conn.commit()

            print(f"\n✓ 成功为 {len(chunk_ids)} 个片段生成并保存向量")

            # 5. 验证结果
            cur.execute(
                """
                SELECT COUNT(*) as total,
                       COUNT(embedding_json) as with_vector
                FROM chunks
                WHERE is_active = true
                """
            )

            result = cur.fetchone()
            print(f"\n数据统计:")
            print(f"  总片段数: {result[0]}")
            print(f"  已有向量: {result[1]}")
            print(f"  完成率: {result[1]/result[0]*100:.1f}%")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n" + "="*60)
    print("向量生成完成！")
    print("="*60)


if __name__ == "__main__":
    print("猴痘知识库向量生成工具")
    print("使用阿里百炼 text-embedding-v4 模型\n")

    try:
        generate_vectors_for_existing_data()
    except Exception as e:
        print(f"\n处理失败: {e}")
        exit(1)
