import os
import sys
import psycopg
from dotenv import load_dotenv

# 添加backend目录到路径，以便导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from embedder_alibaba import embed_text

def init_remote_db(db_url):
    print(f"🚀 开始初始化远程数据库...")
    
    try:
        # 1. 执行 SQL 初始化表结构
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                print("📝 正在创建表结构...")
                with open("init_db.sql", "r", encoding="utf-8") as f:
                    sql = f.read()
                    cur.execute(sql)
                
                # 额外创建咨询记录表（如果不存在）
                cur.execute("""
                CREATE TABLE IF NOT EXISTS user_consultations (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT,
                    antiviral_id TEXT,
                    question TEXT,
                    answer TEXT,
                    risk_type TEXT,
                    region TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
            conn.commit()
            print("✅ 表结构创建成功")

        # 2. 提醒用户运行数据同步
        print("\n👉 数据库结构已就绪！")
        print("下一步请在本地运行以下命令，将知识库数据上传到云端：")
        print(f"DATABASE_URL=\"{db_url}\" python backend/process_data.py")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")

if __name__ == "__main__":
    url = input("请输入 Railway 的 DATABASE_URL: ").strip()
    if url:
        init_remote_db(url)
    else:
        print("未输入连接字符串，取消操作。")
