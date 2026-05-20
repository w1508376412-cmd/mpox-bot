"""向量生成模块 - 使用OpenAI Embedding API生成文本向量"""
from openai import OpenAI
from typing import List
from config import get_settings


settings = get_settings()

# 使用阿里百炼配置生成向量
client_kwargs = {
    "api_key": settings.alibaba_api_key or settings.openai_api_key,
    "base_url": settings.alibaba_api_base or settings.openai_api_base
}
client = OpenAI(**client_kwargs)


def embed_text(text: str) -> List[float]:
    """
    将文本转换为向量

    Args:
        text: 输入文本

    Returns:
        向量（浮点数列表）
    """
    try:
        response = client.embeddings.create(
            model=settings.embedding_model,
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
        batch_size: 批次大小

    Returns:
        向量列表
    """
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = client.embeddings.create(
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
