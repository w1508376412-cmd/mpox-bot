"""数据采集模块 - 从权威来源抓取猴痘相关信息"""
import requests
import trafilatura
from typing import Dict, List
from datetime import date
from schemas import DocumentMetadata


# 权威数据源配置
SOURCES = [
    {
        "id": "who_mpox_fact_sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/mpox",
        "title": "Mpox (monkeypox) - WHO Fact Sheet",
        "source": "WHO",
        "region": "global",
        "topic": ["症状", "传播", "预防", "治疗"],
        "publish_date": date(2024, 8, 1)
    },
    {
        "id": "who_mpox_qa",
        "url": "https://www.who.int/news-room/questions-and-answers/item/monkeypox",
        "title": "Mpox Q&A",
        "source": "WHO",
        "region": "global",
        "topic": ["常见问答", "性接触", "旅行", "居家隔离"],
        "publish_date": date(2024, 7, 15)
    },
    {
        "id": "china_cdc_mpox_2025",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202501/t20250109_303769.html",
        "title": "猴痘病毒Ⅰb亚分支疫情防控知识问答",
        "source": "中国疾控中心",
        "region": "中国",
        "topic": ["症状", "密接管理", "就医建议"],
        "publish_date": date(2025, 1, 9)
    },
    {
        "id": "cdc_mpox_symptoms",
        "url": "https://www.cdc.gov/poxvirus/mpox/symptoms/index.html",
        "title": "Mpox Signs and Symptoms",
        "source": "CDC",
        "region": "美国",
        "topic": ["症状", "诊断"],
        "publish_date": date(2024, 6, 20)
    }
]


def fetch_page(url: str, timeout: int = 20) -> str:
    """
    抓取网页并提取正文内容

    Args:
        url: 网页URL
        timeout: 超时时间（秒）

    Returns:
        提取的正文内容
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        html = response.text

        # 使用trafilatura提取正文
        text = trafilatura.extract(html)
        return text or ""
    except Exception as e:
        print(f"抓取失败 {url}: {e}")
        return ""


def crawl_all_sources(output_dir: str = "data/raw") -> List[DocumentMetadata]:
    """
    抓取所有配置的数据源

    Args:
        output_dir: 输出目录

    Returns:
        文档元数据列表
    """
    documents = []

    for source_config in SOURCES:
        print(f"正在抓取: {source_config['title']}")

        # 抓取网页内容
        content = fetch_page(source_config["url"])

        if not content:
            print(f"  ⚠️  抓取失败，跳过")
            continue

        # 保存原始内容
        source_dir = source_config["source"].lower().replace(" ", "_")
        file_path = f"{output_dir}/{source_dir}/{source_config['id']}.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  ✓ 已保存到 {file_path}")

        # 创建文档元数据
        metadata = DocumentMetadata(
            id=source_config["id"],
            title=source_config["title"],
            source=source_config["source"],
            url=source_config["url"],
            publish_date=source_config["publish_date"],
            region=source_config["region"],
            topic=source_config["topic"]
        )
        documents.append(metadata)

    return documents


if __name__ == "__main__":
    print("开始抓取权威数据源...")
    docs = crawl_all_sources()
    print(f"\n完成！共抓取 {len(docs)} 个文档")
