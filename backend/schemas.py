from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class DocumentMetadata(BaseModel):
    """文档元数据"""
    id: str
    title: str
    source: str
    url: str
    publish_date: date
    region: str
    topic: List[str]


class ChunkData(BaseModel):
    """知识片段数据"""
    id: str
    document_id: str
    content: str
    topic: List[str]
    source: str
    url: str
    publish_date: date
    region: str


class ChatRequest(BaseModel):
    """聊天请求"""
    question: str
    user_name: str  # 用户姓名
    antiviral_id: str  # 抗病毒编号
    region: str = "中国"  # 默认地区


class SourceInfo(BaseModel):
    """来源信息"""
    source: str
    title: str
    url: str
    publish_date: date


class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str
    risk_type: str
    sources: List[SourceInfo]
    follow_up_questions: List[str] = []  # 推荐的后续问题
    disclaimer: str = (
        "本机器人仅提供猴痘/mpox健康科普信息，不能替代医生诊断或治疗。"
        "如出现新发或原因不明皮疹、发热、淋巴结肿大，或有可疑接触史，"
        "请咨询医疗机构或当地疾控部门。"
    )


class ExportWordRequest(BaseModel):
    """导出Word请求"""
    answer: str
    question: str
    user_name: str = ""
    antiviral_id: str = ""
    sources: List[SourceInfo] = []
