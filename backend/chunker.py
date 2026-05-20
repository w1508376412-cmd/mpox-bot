"""文档切片模块 - 将长文档切分成适合检索的片段"""
from typing import List
import uuid


def chunk_text(text: str, size: int = 600, overlap: int = 80) -> List[str]:
    """
    将文本切分成固定大小的片段，带重叠

    Args:
        text: 原始文本
        size: 每个片段的字符数
        overlap: 片段之间的重叠字符数

    Returns:
        文本片段列表
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - overlap

    return chunks


def create_chunk_with_context(
    content: str,
    source: str,
    title: str,
    section: str = ""
) -> str:
    """
    创建带上下文信息的知识片段

    Args:
        content: 片段内容
        source: 来源
        title: 文档标题
        section: 章节标题（可选）

    Returns:
        带上下文的完整片段
    """
    context_parts = [
        f"来源：{source}",
        f"标题：{title}"
    ]

    if section:
        context_parts.append(f"章节：{section}")

    context_parts.append(f"正文：{content}")

    return "\n".join(context_parts)


def process_document(
    text: str,
    metadata: dict,
    chunk_size: int = 600,
    overlap: int = 80
) -> List[dict]:
    """
    处理单个文档，生成带元数据的片段列表

    Args:
        text: 文档文本
        metadata: 文档元数据
        chunk_size: 片段大小
        overlap: 重叠大小

    Returns:
        片段数据列表
    """
    # 切分文本
    raw_chunks = chunk_text(text, size=chunk_size, overlap=overlap)

    # 为每个片段添加元数据
    chunks = []
    for chunk_content in raw_chunks:
        # 创建带上下文的片段
        full_content = create_chunk_with_context(
            content=chunk_content,
            source=metadata["source"],
            title=metadata["title"]
        )

        chunk_data = {
            "id": str(uuid.uuid4()),
            "document_id": metadata["id"],
            "content": full_content,
            "topic": metadata["topic"],
            "source": metadata["source"],
            "url": metadata["url"],
            "publish_date": metadata["publish_date"],
            "region": metadata["region"]
        }
        chunks.append(chunk_data)

    return chunks
