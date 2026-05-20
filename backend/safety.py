"""安全分诊规则模块"""
from typing import Literal

# 高风险关键词
HIGH_RISK_KEYWORDS = [
    "呼吸困难", "意识不清", "抽搐", "眼睛疼", "视力下降",
    "孕妇", "婴儿", "免疫低下", "艾滋", "HIV", "大面积皮疹",
    "严重疼痛", "高烧不退", "持续高热", "昏迷", "休克"
]

# 症状关键词
SYMPTOM_KEYWORDS = [
    "皮疹", "水疱", "脓疱", "发烧", "淋巴结肿大", "发热",
    "接触过猴痘", "密接", "暴露", "肛门疼", "生殖器",
    "皮肤病变", "红疹", "疱疹", "头痛", "肌肉痛", "背痛", "乏力"
]

# 政策相关关键词
POLICY_KEYWORDS = [
    "就医", "医院", "疾控", "隔离", "观察", "检测",
    "报告", "入境", "出境", "旅行", "密接管理"
]

RiskType = Literal["high_risk", "symptom_risk", "policy", "general"]


def classify_question(question: str) -> RiskType:
    """
    对用户问题进行风险分类

    Args:
        question: 用户问题

    Returns:
        风险类型: high_risk, symptom_risk, policy, general
    """
    question_lower = question.lower()

    # 检查高风险关键词
    if any(keyword in question for keyword in HIGH_RISK_KEYWORDS):
        return "high_risk"

    # 检查症状关键词
    if any(keyword in question for keyword in SYMPTOM_KEYWORDS):
        return "symptom_risk"

    # 检查政策关键词
    if any(keyword in question for keyword in POLICY_KEYWORDS):
        return "policy"

    return "general"


def get_safety_prefix(risk_type: RiskType) -> str:
    """
    根据风险类型获取安全提示前缀

    Args:
        risk_type: 风险类型

    Returns:
        安全提示文本
    """
    if risk_type == "high_risk":
        return (
            "⚠️ 重要提示：您描述的情况可能需要紧急医疗关注。"
            "请尽快前往医疗机构就诊或拨打急救电话。\n\n"
        )
    elif risk_type == "symptom_risk":
        return (
            "⚠️ 本机器人仅提供猴痘健康科普信息，不能替代医生诊断或治疗。 "
            "如果您出现疑似症状或可疑接触史，建议尽快咨询医疗机构或当地疾控部门。\n\n"
        )
    return ""
