"""向量生成模块 - 使用阿里百炼API生成文本向量"""
from openai import OpenAI
from typing import List
import json
from config import get_settings


settings = get_settings()

# 创建阿里百炼客户端（用于embedding）
embedding_client = OpenAI(
    api_key=settings.alibaba_api_key,
    base_url=settings.alibaba_api_base
)


def embed_text(text: str) -> List[float]:
    """
    使用阿里百炼API将文本转换为向量

    Args:
        text: 输入文本

    Returns:
        向量（浮点数列表）
    """
    try:
        response = embedding_client.embeddings.create(
            model=settings.embedding_model,  # text-embedding-v4
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"向量生成失败: {e}")
        raise


def embed_batch(texts: List[str], batch_size: int = 10) -> List[List[float]]:
    """
    批量生成向量

    Args:
        texts: 文本列表
        batch_size: 批次大小（阿里百炼限制最多10）

    Returns:
        向量列表
    """
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = embedding_client.embeddings.create(
                model=settings.embedding_model,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            print(f"已处理 {min(i + batch_size, len(texts))}/{len(texts)} 个文本")
        except Exception as e:
            print(f"批次 {i}-{i+batch_size} 处理失败: {e}")
            raise

    return embeddings


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度

    Args:
        vec1: 向量1
        vec2: 向量2

    Returns:
        余弦相似度（0-1之间）
    """
    if vec1 is None or vec2 is None:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def embed_text_to_json(text: str) -> str:
    """
    将文本转换为向量并序列化为JSON字符串

    Args:
        text: 输入文本

    Returns:
        JSON格式的向量字符串
    """
    vector = embed_text(text)
    return json.dumps(vector)
