"""添加示例数据到数据库"""
import psycopg
import os
from datetime import date
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://yanfei@localhost:5432/mpox_bot")

# 示例文档和知识片段
SAMPLE_DATA = [
    {
        "doc_id": "sample_who_001",
        "title": "猴痘基础知识",
        "source": "WHO",
        "url": "https://www.who.int/news-room/fact-sheets/detail/mpox",
        "publish_date": date(2024, 8, 1),
        "region": "global",
        "chunks": [
            {
                "content": "来源：WHO\n标题：猴痘基础知识\n正文：猴痘（mpox）是一种由猴痘病毒引起的病毒性疾病。该病毒可通过与感染者密切接触、污染物品或感染动物传播。症状通常包括皮疹、发热、淋巴结肿大、头痛、肌肉痛、背痛和乏力。",
                "topic": ["症状", "传播", "基础知识"]
            },
            {
                "content": "来源：WHO\n标题：猴痘传播途径\n正文：猴痘主要通过以下方式传播：1) 与感染者的密切接触，包括性接触；2) 接触被污染的物品，如衣物、床单；3) 接触感染的动物。病毒可通过破损的皮肤、呼吸道或眼睛、鼻子、口腔的粘膜进入人体。",
                "topic": ["传播", "预防"]
            },
            {
                "content": "来源：WHO\n标题：猴痘症状识别\n正文：猴痘的症状通常在接触后21天内出现。主要症状包括：发热、头痛、肌肉痛、背痛、淋巴结肿大、乏力。发热后1-3天内会出现皮疹，通常从面部开始，然后扩散到身体其他部位。皮疹会经历斑疹、丘疹、水疱、脓疱和结痂等阶段。",
                "topic": ["症状", "诊断"]
            }
        ]
    },
    {
        "doc_id": "sample_china_cdc_001",
        "title": "猴痘防控知识（中国）",
        "source": "中国疾控中心",
        "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202501/t20250109_303769.html",
        "publish_date": date(2025, 1, 9),
        "region": "中国",
        "chunks": [
            {
                "content": "来源：中国疾控中心\n标题：怀疑感染猴痘怎么办\n正文：如果怀疑自己感染猴痘病毒，应尽快前往医疗机构就诊，并主动告知医生症状和可疑接触史。就医途中请做好个人防护，避免与他人密切接触。不要自行用药或在家观察，应及时寻求专业医疗帮助。",
                "topic": ["就医建议", "症状", "中国政策"]
            },
            {
                "content": "来源：中国疾控中心\n标题：密接者健康监测\n正文：猴痘密切接触者应在疾控机构专业人员指导下进行21天健康监测。监测期间应注意观察是否出现发热、皮疹、淋巴结肿大等症状。如出现任何可疑症状，应立即联系当地疾控部门或就近就医。",
                "topic": ["密接管理", "健康监测", "中国政策"]
            },
            {
                "content": "来源：中国疾控中心\n标题：猴痘预防措施\n正文：预防猴痘的关键措施包括：1) 避免与疑似或确诊患者密切接触；2) 不共用毛巾、床单等个人物品；3) 保持良好的手部卫生；4) 避免接触野生动物；5) 如有可疑接触史，及时联系当地疾控部门。",
                "topic": ["预防", "健康教育"]
            }
        ]
    }
]

def add_sample_data():
    """添加示例数据到数据库"""
    conn = psycopg.connect(DATABASE_URL)

    try:
        with conn.cursor() as cur:
            for doc_data in SAMPLE_DATA:
                # 插入文档
                cur.execute(
                    """
                    INSERT INTO documents (id, title, source, url, publish_date, region)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        doc_data["doc_id"],
                        doc_data["title"],
                        doc_data["source"],
                        doc_data["url"],
                        doc_data["publish_date"],
                        doc_data["region"]
                    )
                )

                # 插入知识片段
                for chunk_data in doc_data["chunks"]:
                    chunk_id = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO chunks
                        (id, document_id, content, topic, source, url, publish_date, region)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            chunk_id,
                            doc_data["doc_id"],
                            chunk_data["content"],
                            chunk_data["topic"],
                            doc_data["source"],
                            doc_data["url"],
                            doc_data["publish_date"],
                            doc_data["region"]
                        )
                    )

                print(f"✓ 已添加文档: {doc_data['title']}")

        conn.commit()
        print("\n✓ 示例数据添加完成！")

        # 统计数据
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents")
            doc_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cur.fetchone()[0]
            print(f"\n数据库统计:")
            print(f"  文档数: {doc_count}")
            print(f"  知识片段数: {chunk_count}")

    finally:
        conn.close()

if __name__ == "__main__":
    print("正在添加示例数据到数据库...")
    add_sample_data()
