"""
抓取国家疾控局和国家卫健委的官方猴痘防控文件
"""
import requests
import trafilatura
import os
import json
from datetime import date

# 国家疾控局和国家卫健委的官方文件
OFFICIAL_SOURCES = [
    {
        "id": "ndcpa_mpox_prevention_plan",
        "url": "https://www.ndcpa.gov.cn/jbkzzx/c100014/common/content/content_1698984403881291776.html",
        "title": "猴痘防控方案",
        "source": "国家疾控局",
        "region": "中国",
        "priority": 1,
        "topic": ["防控方案", "政策", "就医指导", "疫情监测"],
        "publish_date": date(2024, 9, 1)
    },
    {
        "id": "nhc_mpox_technical_guide_2022",
        "url": "https://www.nhc.gov.cn/yjb/c100058/202207/fdaf10006d0b4034bca46a28b5f0bd20.shtml",
        "title": "猴痘防控技术指南（2022年版）",
        "source": "国家卫健委",
        "region": "中国",
        "priority": 1,
        "topic": ["技术指南", "防控", "诊断", "治疗", "隔离"],
        "publish_date": date(2022, 7, 1)
    }
]


def fetch_page(url: str, timeout: int = 30) -> str:
    """抓取网页并提取正文内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        print(f"  正在请求: {url}")
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()

        # 尝试使用正确的编码
        if 'charset' in response.headers.get('content-type', '').lower():
            response.encoding = response.apparent_encoding

        html = response.text

        # 使用trafilatura提取正文
        text = trafilatura.extract(html, include_comments=False, include_tables=True)

        if text:
            print(f"  ✓ 成功提取 {len(text)} 字符")
            return text
        else:
            print(f"  ⚠️  无法提取正文内容")
            return ""

    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        return ""


def save_raw_content(content: str, source_config: dict, output_dir: str = "data/raw"):
    """保存原始内容到文件"""
    # 创建目录
    source_dir = source_config["source"].lower().replace(" ", "_")
    full_dir = f"{output_dir}/{source_dir}"
    os.makedirs(full_dir, exist_ok=True)

    # 保存文件
    file_path = f"{full_dir}/{source_config['id']}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        # 写入元数据
        f.write(f"来源：{source_config['source']}\n")
        f.write(f"标题：{source_config['title']}\n")
        f.write(f"URL：{source_config['url']}\n")
        f.write(f"发布日期：{source_config['publish_date']}\n")
        f.write(f"地区：{source_config['region']}\n")
        f.write(f"优先级：{source_config['priority']}\n")
        f.write(f"主题：{', '.join(source_config['topic'])}\n")
        f.write("\n" + "="*80 + "\n\n")
        f.write(content)

    return file_path


def crawl_official_sources():
    """抓取国家疾控局和国家卫健委的官方文件"""
    print("="*80)
    print("抓取国家疾控局和国家卫健委的官方猴痘防控文件")
    print("="*80)

    successful = []
    failed = []

    for i, source_config in enumerate(OFFICIAL_SOURCES, 1):
        print(f"\n[{i}/{len(OFFICIAL_SOURCES)}] {source_config['title']}")
        print(f"  来源: {source_config['source']}")

        # 抓取网页内容
        content = fetch_page(source_config["url"])

        if not content or len(content) < 100:
            print(f"  ⚠️  内容太少或抓取失败，跳过")
            failed.append(source_config)
            continue

        # 保存原始内容
        try:
            file_path = save_raw_content(content, source_config)
            print(f"  ✓ 已保存到: {file_path}")
            successful.append(source_config)
        except Exception as e:
            print(f"  ❌ 保存失败: {e}")
            failed.append(source_config)

    # 统计结果
    print(f"\n{'='*80}")
    print("抓取完成统计")
    print(f"{'='*80}")
    print(f"总数据源: {len(OFFICIAL_SOURCES)}")
    print(f"成功抓取: {len(successful)}")
    print(f"失败: {len(failed)}")

    if failed:
        print(f"\n失败的数据源:")
        for source in failed:
            print(f"  - {source['title']} ({source['url']})")

    return successful


if __name__ == "__main__":
    print("国家疾控局和国家卫健委官方文件采集工具\n")
    successful = crawl_official_sources()
    print(f"\n✓ 完成！成功抓取 {len(successful)} 个官方文件")
    print(f"\n下一步：运行 python process_data_real.py 来处理数据并生成向量")
