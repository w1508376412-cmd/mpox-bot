"""
增强的检索模块 - 支持优先级和混合检索
当前使用文本匹配，预留向量检索接口
"""
import psycopg
from typing import List, Dict, Any
from config import get_settings
import json

settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding='utf8'
    )


def search_chunks_with_priority(
    question: str,
    region: str = "中国",
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    按优先级检索知识片段

    优先级策略：
    1. 优先返回国内口径（priority=1）
    2. 其次返回国际基准（priority=2）
    3. 最后返回区域疫情（priority=3）

    Args:
        question: 用户问题
        region: 地区
        top_k: 返回结果数量

    Returns:
        相关片段列表
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 使用优先级加权的检索策略
            cur.execute(
                """
                SELECT
                    content,
                    source,
                    url,
                    publish_date,
                    region,
                    priority,
                    CASE
                        WHEN priority = 1 THEN 100  -- 国内口径最高权重
                        WHEN priority = 2 THEN 50   -- 国际基准中等权重
                        WHEN priority = 3 THEN 25   -- 区域疫情较低权重
                        ELSE 10
                    END as priority_weight
                FROM chunks
                WHERE is_active = true
                  AND (region = %s OR region = 'global')
                  AND (
                    content LIKE %s
                    OR content LIKE '%%猴痘%%'
                    OR content LIKE '%%症状%%'
                    OR content LIKE '%%传播%%'
                    OR content LIKE '%%预防%%'
                    OR content LIKE '%%治疗%%'
                  )
                ORDER BY
                    priority ASC,  -- 优先级数字越小越优先
                    CASE
                        WHEN content LIKE %s THEN 1
                        WHEN content LIKE '%%猴痘%%' THEN 2
                        ELSE 3
                    END
                LIMIT %s
                """,
                (region, f'%{question}%', f'%{question}%', top_k)
            )

            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append({
                    "content": row[0],
                    "source": row[1],
                    "url": row[2],
                    "publish_date": row[3],
                    "region": row[4],
                    "priority": row[5]
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
        priority_label = {
            1: "【国内权威】",
            2: "【国际基准】",
            3: "【区域参考】"
        }.get(chunk.get('priority', 2), "")

        context_parts.append(
            f"【资料 {i}】{priority_label}\n"
            f"来源：{chunk['source']}\n"
            f"发布日期：{chunk['publish_date']}\n"
            f"内容：\n{chunk['content']}\n"
        )

    return "\n".join(context_parts)


# 保持向后兼容
def search_chunks(question: str, region: str = "中国", top_k: int = 5) -> List[Dict[str, Any]]:
    """向后兼容的检索接口"""
    return search_chunks_with_priority(question, region, top_k)
