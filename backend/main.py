"""FastAPI主程序 - 猴痘知识问答API"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from schemas import ChatRequest, ChatResponse, SourceInfo, ExportWordRequest
from safety import classify_question
from retriever_vector import search_chunks, format_context, get_db_connection
from generator import generate_answer
from word_export import markdown_to_docx
from config import get_settings
from concurrent.futures import ThreadPoolExecutor
import os
import time
import uuid

settings = get_settings()
KEEPALIVE_INTERVAL_SECONDS = 0.2
KEEPALIVE_CHUNK = "\n" + (" " * 2048)


def ensure_runtime_schema():
    """Apply small, idempotent migrations needed by the current runtime."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        source TEXT NOT NULL,
                        url TEXT NOT NULL,
                        publish_date DATE NOT NULL,
                        region TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chunks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
                        content TEXT NOT NULL,
                        topic TEXT[] NOT NULL,
                        source TEXT NOT NULL,
                        url TEXT NOT NULL,
                        publish_date DATE NOT NULL,
                        region TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT true,
                        version TEXT DEFAULT '1.0',
                        last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_json JSONB")
                cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 2")
                cur.execute("CREATE INDEX IF NOT EXISTS chunks_content_idx ON chunks USING gin(to_tsvector('simple', content))")
                cur.execute("CREATE INDEX IF NOT EXISTS chunks_region_idx ON chunks(region)")
                cur.execute("CREATE INDEX IF NOT EXISTS chunks_is_active_idx ON chunks(is_active)")
                cur.execute("CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_embedding_json ON chunks USING gin(embedding_json)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_priority ON chunks(priority)")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_consultations (
                        id SERIAL PRIMARY KEY,
                        user_name TEXT NOT NULL,
                        antiviral_id TEXT NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        risk_type TEXT NOT NULL,
                        region TEXT DEFAULT '中国',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_consultations_antiviral_id ON user_consultations(antiviral_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_consultations_created_at ON user_consultations(created_at)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_consultations_user_name ON user_consultations(user_name)")
                cur.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cur.fetchone()[0]
                if chunk_count == 0:
                    seed_sample_data(cur)
            conn.commit()
            print("✓ 数据库运行时结构检查完成")
    except Exception as e:
        print(f"数据库运行时结构检查失败: {e}")


def seed_sample_data(cur):
    """Seed a minimal built-in knowledge base when a remote database is empty."""
    sample_data = [
        {
            "doc_id": "sample_who_001",
            "title": "猴痘基础知识",
            "source": "WHO",
            "url": "https://www.who.int/news-room/fact-sheets/detail/mpox",
            "publish_date": "2024-08-01",
            "region": "global",
            "priority": 2,
            "chunks": [
                ("猴痘（mpox）是一种由猴痘病毒引起的病毒性疾病。该病毒可通过与感染者密切接触、污染物品或感染动物传播。症状通常包括皮疹、发热、淋巴结肿大、头痛、肌肉痛、背痛和乏力。", ["症状", "传播", "基础知识"]),
                ("猴痘主要通过与感染者密切接触传播，包括性接触；也可通过接触被污染的衣物、床单等物品，或接触感染动物传播。", ["传播", "预防"]),
                ("猴痘症状通常在接触后21天内出现。主要症状包括发热、头痛、肌肉痛、背痛、淋巴结肿大、乏力。发热后1-3天内会出现皮疹，通常从面部开始，然后扩散到身体其他部位。", ["症状", "诊断"]),
            ],
        },
        {
            "doc_id": "sample_china_cdc_001",
            "title": "猴痘防控知识（中国）",
            "source": "中国疾控中心",
            "url": "https://www.chinacdc.cn/jkkp/crb/ycr/202501/t20250109_303769.html",
            "publish_date": "2025-01-09",
            "region": "中国",
            "priority": 1,
            "chunks": [
                ("如果怀疑自己感染猴痘病毒，应尽快前往医疗机构就诊，并主动告知医生症状和可疑接触史。就医途中请做好个人防护，避免与他人密切接触。", ["就医建议", "症状", "中国政策"]),
                ("猴痘密切接触者应在疾控机构专业人员指导下进行21天健康监测。监测期间应注意观察是否出现发热、皮疹、淋巴结肿大等症状。", ["密接管理", "健康监测", "中国政策"]),
                ("预防猴痘的关键措施包括：避免与疑似或确诊患者密切接触；不共用毛巾、床单等个人物品；保持良好的手部卫生；避免接触野生动物。", ["预防", "健康教育"]),
            ],
        },
    ]

    for doc in sample_data:
        cur.execute(
            """
            INSERT INTO documents (id, title, source, url, publish_date, region)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (doc["doc_id"], doc["title"], doc["source"], doc["url"], doc["publish_date"], doc["region"])
        )
        for content, topic in doc["chunks"]:
            cur.execute(
                """
                INSERT INTO chunks
                (id, document_id, content, topic, source, url, publish_date, region, priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    doc["doc_id"],
                    content,
                    topic,
                    doc["source"],
                    doc["url"],
                    doc["publish_date"],
                    doc["region"],
                    doc["priority"],
                )
            )
    print("✓ 空数据库已写入基础知识库样例数据")


def save_consultation(user_name: str, antiviral_id: str, question: str, answer: str, risk_type: str, region: str):
    """保存用户咨询记录到数据库"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_consultations
                    (user_name, antiviral_id, question, answer, risk_type, region)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_name, antiviral_id, question, answer, risk_type, region)
                )
            conn.commit()
            print(f"✓ 已保存咨询记录: {user_name} ({antiviral_id})")
    except Exception as e:
        print(f"保存咨询记录失败: {e}")


app = FastAPI(
    title="猴痘知识问答机器人",
    description="基于权威来源的猴痘/mpox健康科普问答系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    ensure_runtime_schema()


# 挂载静态文件
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "猴痘知识问答机器人API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "mpox-bot"}


@app.post("/export-word")
async def export_word(request: ExportWordRequest):
    """
    将回答导出为Word文档

    Args:
        request: 包含回答内容和用户信息的请求

    Returns:
        Word文档（docx）文件流
    """
    try:
        # 转换来源为dict格式
        sources_data = [
            {
                "source": s.source,
                "url": s.url,
                "publish_date": str(s.publish_date)
            }
            for s in request.sources
        ]

        # 生成Word文档
        doc_stream = markdown_to_docx(
            markdown_text=request.answer,
            question=request.question,
            user_name=request.user_name,
            antiviral_id=request.antiviral_id,
            sources=sources_data
        )

        # 生成文件名
        from urllib.parse import quote
        filename = f"猴痘问答_{request.user_name}_{request.question[:20]}.docx"
        encoded_filename = quote(filename)

        return StreamingResponse(
            doc_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except Exception as e:
        print(f"导出Word失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


def build_chat_response(request: ChatRequest) -> ChatResponse:
    """
    Build the chat response synchronously.

    Args:
        request: 包含用户问题和地区的请求

    Returns:
        包含回答、风险类型和来源的响应
    """
    # 1. 风险分类
    risk_type = classify_question(request.question)

    # 2. 检索相关知识片段
    chunks = search_chunks(
        question=request.question,
        region=request.region,
        top_k=5
    )

    if not chunks:
        return ChatResponse(
            answer="抱歉，暂时没有找到足够相关的资料。请尝试换个问法，或直接咨询医疗机构。",
            risk_type=risk_type,
            sources=[],
            follow_up_questions=[]
        )

    # 3. 格式化上下文
    context = format_context(chunks)

    # 4. 生成回答
    answer, follow_up_questions = generate_answer(
        question=request.question,
        context=context,
        risk_type=risk_type
    )

    # 5. 提取来源信息
    sources = [
        SourceInfo(
            source=chunk["source"],
            title=chunk["title"],
            url=chunk["url"],
            publish_date=chunk["publish_date"]
        )
        for chunk in chunks
    ]

    # 去重来源
    unique_sources = []
    seen = set()
    for source in sources:
        key = (source.source, source.title, source.url)
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)

    # 6. 保存用户咨询记录
    save_consultation(
        user_name=request.user_name,
        antiviral_id=request.antiviral_id,
        question=request.question,
        answer=answer,
        risk_type=risk_type,
        region=request.region
    )

    return ChatResponse(
        answer=answer,
        risk_type=risk_type,
        sources=unique_sources,
        follow_up_questions=follow_up_questions
    )


def stream_chat_response(request: ChatRequest):
    # Send JSON whitespace while the model is generating so deployment proxies do not
    # close an otherwise-idle request. Leading whitespace is valid before JSON.
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(build_chat_response, request)
            while not future.done():
                yield KEEPALIVE_CHUNK
                time.sleep(KEEPALIVE_INTERVAL_SECONDS)
            yield future.result().model_dump_json()

    except HTTPException:
        raise
    except Exception as e:
        print(f"处理请求时出错: {e}")
        yield ChatResponse(
            answer="抱歉，服务暂时不可用。请稍后再试或直接咨询医疗机构。",
            risk_type="general",
            sources=[],
            follow_up_questions=[]
        ).model_dump_json()


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    问答接口

    Args:
        request: 包含用户问题和地区的请求

    Returns:
        包含回答、风险类型和来源的响应
    """
    return StreamingResponse(
        stream_chat_response(request),
        media_type="application/json"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
