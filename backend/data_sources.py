"""
三级优先级数据源配置
按照国内口径 → 国际基准 → 区域疫情的优先级构建知识库
"""
from datetime import date

# 优先级定义
PRIORITY_DOMESTIC = 1  # 国内回答口径
PRIORITY_INTERNATIONAL = 2  # 国际医学与流行病学基准
PRIORITY_REGIONAL = 3  # 区域疫情与监测

# 完整数据源配置
COMPREHENSIVE_SOURCES = [
    # ========== 第一优先级：国内回答口径 ==========
    {
        "id": "china_nhc_mpox_prevention",
        "url": "http://www.nhc.gov.cn/",  # 国家卫健委
        "title": "国家卫健委猴痘防控指南",
        "source": "国家卫健委",
        "region": "中国",
        "priority": PRIORITY_DOMESTIC,
        "topic": ["防控", "政策", "就医指导"],
        "publish_date": date(2025, 1, 1),
        "description": "中国大陆官方防控政策和就医指导"
    },
    {
        "id": "china_cdc_mpox_2025",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202501/t20250109_303769.html",
        "title": "猴痘病毒Ⅰb亚分支疫情防控知识问答",
        "source": "中国疾控中心",
        "region": "中国",
        "priority": PRIORITY_DOMESTIC,
        "topic": ["症状", "密接管理", "就医建议", "防控措施"],
        "publish_date": date(2025, 1, 9),
        "description": "中国疾控中心官方科普和防控指导"
    },
    {
        "id": "china_cdc_mpox_health_tips",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202507/t20250721_308585.html",
        "title": "猴痘健康防护提示",
        "source": "中国疾控中心",
        "region": "中国",
        "priority": PRIORITY_DOMESTIC,
        "topic": ["预防", "健康教育", "公众指导"],
        "publish_date": date(2025, 7, 21),
        "description": "面向公众的健康防护建议"
    },

    # ========== 第二优先级：国际医学与流行病学基准 ==========
    {
        "id": "who_mpox_fact_sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/mpox",
        "title": "Mpox (monkeypox) - WHO Fact Sheet",
        "source": "WHO",
        "region": "global",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["症状", "传播", "预防", "治疗", "疫苗"],
        "publish_date": date(2024, 8, 1),
        "description": "WHO官方猴痘事实清单"
    },
    {
        "id": "who_mpox_qa",
        "url": "https://www.who.int/news-room/questions-and-answers/item/monkeypox",
        "title": "Mpox Q&A",
        "source": "WHO",
        "region": "global",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["常见问答", "性接触", "旅行", "居家隔离"],
        "publish_date": date(2024, 7, 15),
        "description": "WHO常见问题解答"
    },
    {
        "id": "who_mpox_outbreak",
        "url": "https://www.who.int/emergencies/disease-outbreak-news/item/2024-DON534",
        "title": "WHO Mpox Outbreak Updates",
        "source": "WHO",
        "region": "global",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["疫情动态", "全球监测", "风险评估"],
        "publish_date": date(2024, 12, 1),
        "description": "WHO疫情更新和风险评估"
    },
    {
        "id": "cdc_mpox_about",
        "url": "https://www.cdc.gov/poxvirus/mpox/about/index.html",
        "title": "About Mpox",
        "source": "CDC",
        "region": "美国",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["基础知识", "病毒学", "流行病学"],
        "publish_date": date(2024, 6, 20),
        "description": "CDC猴痘基础知识"
    },
    {
        "id": "cdc_mpox_symptoms",
        "url": "https://www.cdc.gov/poxvirus/mpox/symptoms/index.html",
        "title": "Mpox Signs and Symptoms",
        "source": "CDC",
        "region": "美国",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["症状", "诊断", "临床表现"],
        "publish_date": date(2024, 6, 20),
        "description": "CDC症状识别指南"
    },
    {
        "id": "cdc_mpox_prevention",
        "url": "https://www.cdc.gov/poxvirus/mpox/prevention/index.html",
        "title": "Mpox Prevention",
        "source": "CDC",
        "region": "美国",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["预防", "疫苗", "暴露后预防"],
        "publish_date": date(2024, 6, 20),
        "description": "CDC预防措施指南"
    },
    {
        "id": "cdc_mpox_treatment",
        "url": "https://www.cdc.gov/poxvirus/mpox/clinicians/treatment.html",
        "title": "Mpox Treatment Information",
        "source": "CDC",
        "region": "美国",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["治疗", "临床管理", "抗病毒药物"],
        "publish_date": date(2024, 6, 20),
        "description": "CDC治疗指南"
    },
    {
        "id": "ecdc_mpox_factsheet",
        "url": "https://www.ecdc.europa.eu/en/mpox",
        "title": "ECDC Mpox Factsheet",
        "source": "ECDC",
        "region": "欧洲",
        "priority": PRIORITY_INTERNATIONAL,
        "topic": ["欧洲疫情", "监测", "防控措施"],
        "publish_date": date(2024, 9, 1),
        "description": "欧洲疾控中心猴痘信息"
    },

    # ========== 第三优先级：区域疫情与监测 ==========
    {
        "id": "africa_cdc_mpox",
        "url": "https://africacdc.org/disease/monkeypox/",
        "title": "Africa CDC Mpox Information",
        "source": "Africa CDC",
        "region": "非洲",
        "priority": PRIORITY_REGIONAL,
        "topic": ["非洲疫情", "区域监测", "公共卫生响应"],
        "publish_date": date(2024, 10, 1),
        "description": "非洲疾控中心猴痘信息"
    },
    {
        "id": "ukhsa_mpox",
        "url": "https://www.gov.uk/government/collections/monkeypox-guidance",
        "title": "UKHSA Mpox Guidance",
        "source": "UKHSA",
        "region": "英国",
        "priority": PRIORITY_REGIONAL,
        "topic": ["英国疫情", "旅行建议", "公共卫生措施"],
        "publish_date": date(2024, 8, 15),
        "description": "英国卫生安全局猴痘指南"
    },
    {
        "id": "hk_chp_mpox",
        "url": "https://www.chp.gov.hk/tc/healthtopics/content/24/102466.html",
        "title": "香港卫生防护中心猴痘专页",
        "source": "香港卫生防护中心",
        "region": "香港",
        "priority": PRIORITY_REGIONAL,
        "topic": ["香港疫情", "入境政策", "本地防控"],
        "publish_date": date(2024, 9, 1),
        "description": "香港地区猴痘防控信息"
    }
]

# 按优先级分组
def get_sources_by_priority(priority: int):
    """获取指定优先级的数据源"""
    return [s for s in COMPREHENSIVE_SOURCES if s["priority"] == priority]

# 获取所有数据源URL列表
def get_all_source_urls():
    """获取所有数据源的URL列表"""
    return [s["url"] for s in COMPREHENSIVE_SOURCES]

# 获取数据源统计
def get_source_statistics():
    """获取数据源统计信息"""
    return {
        "total": len(COMPREHENSIVE_SOURCES),
        "priority_1_domestic": len(get_sources_by_priority(PRIORITY_DOMESTIC)),
        "priority_2_international": len(get_sources_by_priority(PRIORITY_INTERNATIONAL)),
        "priority_3_regional": len(get_sources_by_priority(PRIORITY_REGIONAL))
    }
