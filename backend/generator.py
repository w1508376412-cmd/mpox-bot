"""回答生成模块 - 使用大模型基于检索内容生成回答"""
from openai import OpenAI
from typing import List, Dict, Any, Tuple
from config import get_settings
from safety import RiskType, get_safety_prefix
import json


settings = get_settings()
client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_api_base if settings.openai_api_base else None,
    timeout=settings.chat_timeout_seconds,
    max_retries=0
)


def load_system_prompt() -> str:
    """加载系统提示词"""
    return (
        "你是猴痘/mpox健康科普问答助手。只能根据资料回答，不做医学诊断。"
        "症状或接触史相关问题必须建议咨询医疗机构或当地疾控。"
        "回答要简洁、中文、友好，只输出合法JSON。"
    )


def generate_answer(
    question: str,
    context: str,
    risk_type: RiskType
) -> Tuple[str, List[str]]:
    """
    基于检索内容生成回答和推荐问题

    Args:
        question: 用户问题
        context: 检索到的上下文
        risk_type: 风险类型

    Returns:
        (回答内容, 推荐问题列表)
    """
    system_prompt = load_system_prompt()

    risk_instructions = {
        "high_risk": "用户描述了高风险症状，必须明确建议尽快就医或拨打急救电话。",
        "symptom_risk": "用户描述了症状，必须说明无法在线诊断，建议咨询医疗机构或疾控部门。",
        "policy": "优先引用用户所在地区的疾控机构信息。",
        "general": ""
    }

    compact_context = context[:900]
    user_prompt = f"""{risk_instructions.get(risk_type, "")}
资料：{compact_context}
问题：{question}
请只输出JSON：{{"answer":"简洁中文回答，markdown格式，不写参考来源","follow_up_questions":["问题1","问题2","问题3"]}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            extra_body={"thinking": {"type": "disabled"}},
            temperature=0.3,
            max_tokens=300
        )

        raw = response.choices[0].message.content

        # 尝试解析JSON
        try:
            # 清理可能的markdown代码块标记
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            answer = parsed.get("answer", raw)
            follow_up = parsed.get("follow_up_questions", [])
        except (json.JSONDecodeError, Exception):
            answer = raw
            follow_up = []

        # 二次清理：防止AI不听话在answer里又写了一遍参考来源
        import re
        answer = re.split(r'\n(#{1,4}\s*)?参考来源[:：]', answer)[0]
        answer = re.split(r'\n(#{1,4}\s*)?资料来源[:：]', answer)[0]
        answer = answer.strip()

        safety_prefix = get_safety_prefix(risk_type)
        return safety_prefix + answer, follow_up

    except Exception as e:
        print(f"生成回答失败: {e}")
        return "抱歉，我暂时无法回答您的问题。请稍后再试或直接咨询医疗机构。", []
