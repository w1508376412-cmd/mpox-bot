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
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "system_prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


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

    user_prompt = f"""{risk_instructions.get(risk_type, "")}

【资料】
{context}

【用户问题】
{question}

请严格按照以下JSON格式回答，不要输出任何JSON之外的内容：
{{
  "answer": "你的回答内容（使用markdown格式，可以用**加粗**、- 列表 等）",
  "follow_up_questions": ["推荐问题1", "推荐问题2", "推荐问题3"]
}}

要求：
1. answer中直接回答问题，内容简洁清晰，使用markdown格式排版
2. follow_up_questions给出3个用户可能会继续追问的相关问题
3. **绝对不要**在answer中包含"参考来源"或"资料来源"章节，也**不要**在正文中使用"（来源：xxx）"或"据xxx报道"等行内引用，来源信息系统会自动在卡片下方统一展示
4. 如果涉及症状，必须建议就医
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
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
