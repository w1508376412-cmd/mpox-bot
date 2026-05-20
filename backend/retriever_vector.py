"""
向量检索模块 - 使用阿里百炼embedding + 余弦相似度
支持三级优先级策略
"""
import psycopg
from typing import List, Dict, Any
import json
from embedder_alibaba import embed_text, cosine_similarity
from config import get_settings

settings = get_settings()


def get_db_connection():
    """获取数据库连接"""
    return psycopg.connect(
        settings.database_url,
        client_encoding='utf8'
    )


def search_chunks_vector(
    question: str,
    region: str = "中国",
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    使用向量相似度检索知识片段（支持优先级）

    检索策略：
    1. 生成问题的向量
    2. 从数据库获取所有候选片段及其向量
    3. 计算余弦相似度
    4. 按优先级和相似度排序

    Args:
        question: 用户问题
        region: 地区
        top_k: 返回结果数量

    Returns:
        相关片段列表
    """
    try:
        # 1. 生成问题向量
        print(f"正在生成问题向量...")
        question_vector = embed_text(question)

        # 2. 从数据库获取候选片段（使用pgvector的余弦相似度算子 <=>）
        # 注意：1 - (vector <=> question_vector) = cosine similarity
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        c.content, c.source, c.url, c.publish_date, c.region, c.priority,
                        1 - (c.embedding <=> %s::vector) as similarity,
                        d.title
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE c.is_active = true
                      AND (c.region = %s OR c.region = 'global')
                      AND c.embedding IS NOT NULL
                    ORDER BY 
                        similarity DESC -- 先按相似度排，取足够的候选进行重排
                    LIMIT %s
                    """,
                    (question_vector, region, top_k * 4) # 取更多候选
                )

                rows = cur.fetchall()

                if not rows:
                    print("警告：数据库中没有匹配的向量数据，回退到文本匹配")
                    return search_chunks_text_fallback(question, region, top_k)

                # 3. 计算加权分数并重新排序
                results = []
                for row in rows:
                    content, source, url, publish_date, region_val, priority, similarity, title = row

                    if similarity is None: similarity = 0.0

                    # 优先级权重 (稍微调低权重差距，避免 Level 1 绝对霸屏)
                    priority_weight = {
                        1: 1.5, 
                        2: 1.2,
                        3: 1.0
                    }.get(priority, 1.0)

                    # 时间加权 (扩大近期资料的加成范围)
                    import datetime
                    days_diff = (datetime.date(2026, 5, 18) - publish_date).days
                    if days_diff <= 60: 
                        time_weight = 1.8
                    elif days_diff <= 365:
                        time_weight = 1.3
                    else:
                        time_weight = 1.0
                    
                    # 语义锚定加成：如果相似度极高，给予额外权重确保针对性内容不被淹没
                    semantic_boost = 1.5 if similarity > 0.7 else 1.0

                    weighted_score = similarity * priority_weight * time_weight * semantic_boost

                    results.append({
                        "content": content,
                        "source": source,
                        "title": title,
                        "url": url,
                        "publish_date": publish_date,
                        "region": region_val,
                        "priority": priority,
                        "similarity": similarity,
                        "weighted_score": weighted_score
                    })

                # 4. 按最终加权分数排序
                results.sort(key=lambda x: x["weighted_score"], reverse=True)

                # 5. 返回top_k结果
                return results[:top_k]

    except Exception as e:
        print(f"向量检索失败: {e}")
        print("回退到文本匹配模式")
        return search_chunks_text_fallback(question, region, top_k)


def search_chunks_text_fallback(
    question: str,
    region: str = "中国",
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    文本匹配回退方案（当向量检索失败时使用）

    Args:
        question: 用户问题
        region: 地区
        top_k: 返回结果数量

    Returns:
        相关片段列表
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            search_pattern = f'%{question}%'

            cur.execute(
                """
                SELECT c.content, c.source, c.url, c.publish_date, c.region, c.priority, d.title
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.is_active = true
                  AND (c.region = %s OR c.region = 'global')
                  AND (
                    c.content LIKE %s
                    OR c.content LIKE '%%猴痘%%'
                    OR c.content LIKE '%%症状%%'
                    OR c.content LIKE '%%传播%%'
                  )
                ORDER BY
                    c.priority ASC,
                    CASE
                        WHEN c.content LIKE %s THEN 1
                        WHEN c.content LIKE '%%猴痘%%' THEN 2
                        ELSE 3
                    END
                LIMIT %s
                """,
                (region, search_pattern, search_pattern, top_k)
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
                    "priority": row[5],
                    "title": row[6]
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

        # 如果有相似度信息，显示出来
        similarity_info = ""
        if 'similarity' in chunk:
            similarity_info = f" (相似度: {chunk['similarity']:.2%})"

        context_parts.append(
            f"【资料 {i}】{priority_label} (发布日期: {chunk['publish_date']}){similarity_info}\n"
            f"来源：{chunk['source']}\n"
            f"内容：\n{chunk['content']}\n"
        )

    return "\n".join(context_parts)


# 主检索接口（向后兼容）
def search_chunks(question: str, region: str = "中国", top_k: int = 5) -> List[Dict[str, Any]]:
    """
    主检索接口 - 自动选择向量检索或文本匹配

    Args:
        question: 用户问题
        region: 地区
        top_k: 返回结果数量

    Returns:
        相关片段列表
    """
    return search_chunks_vector(question, region, top_k)
