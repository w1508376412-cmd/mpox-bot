"""检索模块 - 基于文本匹配检索相关知识片段（简化版）"""
import psycopg
from typing import List, Dict, Any
from config import get_settings


settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding='utf8'
    )


def search_chunks(
    question: str,
    region: str = "中国",
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    检索与问题最相关的知识片段（使用简单的LIKE匹配）

    Args:
        question: 用户问题
        region: 地区（中国/美国/全球）
        top_k: 返回结果数量

    Returns:
        相关片段列表
    """
    # 连接数据库并检索
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 使用参数化查询，避免SQL中的中文编码问题
            search_pattern = f"%{question}%"
            keyword1 = "%猴痘%"
            keyword2 = "%症状%"
            keyword3 = "%传播%"

            cur.execute(
                """
                SELECT content, source, url, publish_date, region
                FROM chunks
                WHERE is_active = true
                  AND (region = %s OR region = %s)
                  AND (
                    content LIKE %s
                    OR content LIKE %s
                    OR content LIKE %s
                    OR content LIKE %s
                  )
                ORDER BY
                  CASE
                    WHEN content LIKE %s THEN 1
                    WHEN content LIKE %s THEN 2
                    ELSE 3
                  END
                LIMIT %s
                """,
                (region, 'global', search_pattern, keyword1, keyword2, keyword3, search_pattern, keyword1, top_k)
            )

            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append({
                    "content": row[0],
                    "source": row[1],
                    "url": row[2],
                    "publish_date": row[3],
                    "region": row[4]
                })

            return results


def format_context(chunks: List[Dict[str, Any]]) -> str:
    """
    将检索到的片段格式化为上下文

    Args:
        chunks: 片段列表

    Returns:
        格式化的上下文文本
    """
    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"【资料 {i}】\n"
            f"来源：{chunk['source']}\n"
            f"发布日期：{chunk['publish_date']}\n"
            f"内容：\n{chunk['content']}\n"
        )

    return "\n".join(context_parts)
