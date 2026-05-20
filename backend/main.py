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
import os

settings = get_settings()


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


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    问答接口

    Args:
        request: 包含用户问题和地区的请求

    Returns:
        包含回答、风险类型和来源的响应
    """
    try:
        # 1. 风险分类
        risk_type = classify_question(request.question)

        # 2. 检索相关知识片段
        chunks = search_chunks(
            question=request.question,
            region=request.region,
            top_k=5
        )

        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="未找到相关资料，请尝试换个问法或直接咨询医疗机构"
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

    except HTTPException:
        raise
    except Exception as e:
        print(f"处理请求时出错: {e}")
        raise HTTPException(
            status_code=500,
            detail="服务暂时不可用，请稍后再试"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
