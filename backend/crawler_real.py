"""
真实数据采集模块 - 从权威来源抓取猴痘相关信息
按照三级优先级策略抓取数据
"""
import requests
import trafilatura
from typing import Dict, List
from datetime import date
import os
import time


# 第一优先级：国内回答口径
PRIORITY_1_SOURCES = [
    {
        "id": "china_cdc_mpox_2025_01",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202501/t20250109_303769.html",
        "title": "猴痘病毒Ⅰb亚分支疫情防控知识问答",
        "source": "中国疾控中心",
        "region": "中国",
        "priority": 1,
        "topic": ["症状", "密接管理", "就医建议", "防控措施"],
        "publish_date": date(2025, 1, 9)
    },
    {
        "id": "china_cdc_mpox_health_tips",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202507/t20250721_308585.html",
        "title": "猴痘健康防护提示",
        "source": "中国疾控中心",
        "region": "中国",
        "priority": 1,
        "topic": ["预防", "健康教育", "公众指导"],
        "publish_date": date(2025, 7, 21)
    },
    {
        "id": "china_cdc_mpox_basic",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/",
        "title": "中国疾控中心猴痘专题",
        "source": "中国疾控中心",
        "region": "中国",
        "priority": 1,
        "topic": ["基础知识", "防控", "科普"],
        "publish_date": date(2024, 12, 1)
    },
    {
        "id": "nhc_mpox_prevention",
        "url": "http://www.nhc.gov.cn/jkj/s7923/202208/d2e6b9826a7d4e3fa3e8f0b0b8c0e0e0.shtml",
        "title": "国家卫健委猴痘防控方案",
        "source": "国家卫健委",
        "region": "中国",
        "priority": 1,
        "topic": ["防控方案", "政策", "就医指导"],
        "publish_date": date(2024, 8, 1)
    }
]

# 第二优先级：国际医学与流行病学基准
PRIORITY_2_SOURCES = [
    {
        "id": "who_mpox_fact_sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/mpox",
        "title": "Mpox (monkeypox) - WHO Fact Sheet",
        "source": "WHO",
        "region": "global",
        "priority": 2,
        "topic": ["症状", "传播", "预防", "治疗", "疫苗"],
        "publish_date": date(2024, 8, 1)
    },
    {
        "id": "who_mpox_qa",
        "url": "https://www.who.int/news-room/questions-and-answers/item/monkeypox",
        "title": "Mpox Q&A",
        "source": "WHO",
        "region": "global",
        "priority": 2,
        "topic": ["常见问答", "性接触", "旅行", "居家隔离"],
        "publish_date": date(2024, 7, 15)
    },
    {
        "id": "cdc_mpox_about",
        "url": "https://www.cdc.gov/poxvirus/mpox/about/index.html",
        "title": "About Mpox - CDC",
        "source": "CDC",
        "region": "美国",
        "priority": 2,
        "topic": ["基础知识", "病毒学", "流行病学"],
        "publish_date": date(2024, 6, 20)
    },
    {
        "id": "cdc_mpox_symptoms",
        "url": "https://www.cdc.gov/poxvirus/mpox/symptoms/index.html",
        "title": "Mpox Signs and Symptoms - CDC",
        "source": "CDC",
        "region": "美国",
        "priority": 2,
        "topic": ["症状", "诊断", "临床表现"],
        "publish_date": date(2024, 6, 20)
    },
    {
        "id": "cdc_mpox_prevention",
        "url": "https://www.cdc.gov/poxvirus/mpox/prevention/index.html",
        "title": "Mpox Prevention - CDC",
        "source": "CDC",
        "region": "美国",
        "priority": 2,
        "topic": ["预防", "疫苗", "暴露后预防"],
        "publish_date": date(2024, 6, 20)
    },
    {
        "id": "ecdc_mpox_factsheet",
        "url": "https://www.ecdc.europa.eu/en/mpox",
        "title": "ECDC Mpox Factsheet",
        "source": "ECDC",
        "region": "欧洲",
        "priority": 2,
        "topic": ["欧洲疫情", "监测", "防控措施"],
        "publish_date": date(2024, 9, 1)
    }
]

# 第三优先级：区域疫情与监测
PRIORITY_3_SOURCES = [
    {
        "id": "africa_cdc_mpox",
        "url": "https://africacdc.org/disease/monkeypox/",
        "title": "Africa CDC Mpox Information",
        "source": "Africa CDC",
        "region": "非洲",
        "priority": 3,
        "topic": ["非洲疫情", "区域监测", "公共卫生响应"],
        "publish_date": date(2024, 10, 1)
    },
    {
        "id": "hk_chp_mpox",
        "url": "https://www.chp.gov.hk/tc/healthtopics/content/24/102466.html",
        "title": "香港卫生防护中心猴痘专页",
        "source": "香港卫生防护中心",
        "region": "香港",
        "priority": 3,
        "topic": ["香港疫情", "入境政策", "本地防控"],
        "publish_date": date(2024, 9, 1)
    }
]

# 合并所有数据源
ALL_SOURCES = PRIORITY_1_SOURCES + PRIORITY_2_SOURCES + PRIORITY_3_SOURCES


def fetch_page(url: str, timeout: int = 30) -> str:
    """
    抓取网页并提取正文内容

    Args:
        url: 网页URL
        timeout: 超时时间（秒）

    Returns:
        提取的正文内容
    """
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

    except requests.exceptions.Timeout:
        print(f"  ❌ 超时: {url}")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"  ❌ 请求失败: {e}")
        return ""
    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        return ""


def save_raw_content(content: str, source_config: Dict, output_dir: str = "data/raw"):
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


def crawl_all_sources(output_dir: str = "data/raw"):
    """
    抓取所有配置的数据源

    Args:
        output_dir: 输出目录

    Returns:
        成功抓取的数据源列表
    """
    print("="*80)
    print("开始抓取权威数据源")
    print("="*80)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    successful = []
    failed = []

    # 按优先级分组显示
    priority_groups = {
        1: ("第一优先级：国内回答口径", PRIORITY_1_SOURCES),
        2: ("第二优先级：国际医学与流行病学基准", PRIORITY_2_SOURCES),
        3: ("第三优先级：区域疫情与监测", PRIORITY_3_SOURCES)
    }

    for priority, (group_name, sources) in priority_groups.items():
        print(f"\n{'='*80}")
        print(f"{group_name}")
        print(f"{'='*80}\n")

        for i, source_config in enumerate(sources, 1):
            print(f"[{i}/{len(sources)}] {source_config['title']}")
            print(f"  来源: {source_config['source']}")

            # 抓取网页内容
            content = fetch_page(source_config["url"])

            if not content or len(content) < 100:
                print(f"  ⚠️  内容太少或抓取失败，跳过")
                failed.append(source_config)
                continue

            # 保存原始内容
            try:
                file_path = save_raw_content(content, source_config, output_dir)
                print(f"  ✓ 已保存到: {file_path}")
                successful.append(source_config)
            except Exception as e:
                print(f"  ❌ 保存失败: {e}")
                failed.append(source_config)

            # 避免请求过快
            time.sleep(2)

    # 统计结果
    print(f"\n{'='*80}")
    print("抓取完成统计")
    print(f"{'='*80}")
    print(f"总数据源: {len(ALL_SOURCES)}")
    print(f"成功抓取: {len(successful)}")
    print(f"失败: {len(failed)}")

    if failed:
        print(f"\n失败的数据源:")
        for source in failed:
            print(f"  - {source['title']} ({source['url']})")

    return successful


if __name__ == "__main__":
    print("猴痘知识库数据采集工具")
    print("按照三级优先级策略抓取权威数据源\n")

    successful = crawl_all_sources()

    print(f"\n✓ 完成！成功抓取 {len(successful)} 个数据源")
    print(f"\n下一步：运行 python process_data.py 来处理数据并生成向量")
