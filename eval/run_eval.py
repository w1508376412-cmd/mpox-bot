"""评估脚本 - 测试机器人回答质量"""
import json
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from safety import classify_question
from retriever import search_chunks, format_context
from generator import generate_answer


def load_test_questions():
    """加载测试问题"""
    with open('test_questions.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate_answer(question_data: dict, answer: str, risk_type: str) -> dict:
    """
    评估回答质量

    Args:
        question_data: 测试问题数据
        answer: 生成的回答
        risk_type: 风险类型

    Returns:
        评估结果
    """
    results = {
        "question_id": question_data["id"],
        "question": question_data["question"],
        "category": question_data["category"],
        "answer": answer,
        "risk_type": risk_type,
        "checks": {}
    }

    # 检查必须包含的要点
    if "expected_points" in question_data:
        points_found = []
        for point in question_data["expected_points"]:
            if any(keyword in answer for keyword in point.split()):
                points_found.append(point)
        results["checks"]["expected_points"] = {
            "total": len(question_data["expected_points"]),
            "found": len(points_found),
            "details": points_found
        }

    # 检查必须引用的来源
    if "must_cite" in question_data:
        sources_found = []
        for source in question_data["must_cite"]:
            if source in answer:
                sources_found.append(source)
        results["checks"]["must_cite"] = {
            "total": len(question_data["must_cite"]),
            "found": len(sources_found),
            "details": sources_found
        }

    # 检查不应该说的话
    if "must_not_say" in question_data:
        violations = []
        for phrase in question_data["must_not_say"]:
            if phrase in answer:
                violations.append(phrase)
        results["checks"]["must_not_say"] = {
            "violations": violations,
            "passed": len(violations) == 0
        }

    # 检查风险类型是否正确
    if "risk_type" in question_data:
        results["checks"]["risk_type"] = {
            "expected": question_data["risk_type"],
            "actual": risk_type,
            "passed": question_data["risk_type"] == risk_type
        }

    return results


def run_evaluation(region: str = "中国", limit: int = None):
    """
    运行评估

    Args:
        region: 测试地区
        limit: 限制测试数量
    """
    questions = load_test_questions()
    if limit:
        questions = questions[:limit]

    print(f"开始评估 - 共 {len(questions)} 个问题")
    print("="*60)

    results = []
    for i, question_data in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] {question_data['question']}")

        try:
            # 分类
            risk_type = classify_question(question_data["question"])
            print(f"  风险类型: {risk_type}")

            # 检索
            chunks = search_chunks(question_data["question"], region=region, top_k=5)
            if not chunks:
                print("  ⚠️  未找到相关资料")
                continue

            # 生成回答
            context = format_context(chunks)
            answer = generate_answer(
                question=question_data["question"],
                context=context,
                risk_type=risk_type
            )

            # 评估
            result = evaluate_answer(question_data, answer, risk_type)
            results.append(result)

            # 显示评估结果
            if "expected_points" in result["checks"]:
                ep = result["checks"]["expected_points"]
                print(f"  要点覆盖: {ep['found']}/{ep['total']}")

            if "must_cite" in result["checks"]:
                mc = result["checks"]["must_cite"]
                print(f"  来源引用: {mc['found']}/{mc['total']}")

            if "must_not_say" in result["checks"]:
                mns = result["checks"]["must_not_say"]
                if not mns["passed"]:
                    print(f"  ⚠️  违规用语: {mns['violations']}")

        except Exception as e:
            print(f"  ❌ 错误: {e}")

    # 保存结果
    output_file = "evaluation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"评估完成！结果已保存到 {output_file}")

    # 统计
    total = len(results)
    if total > 0:
        avg_points = sum(
            r["checks"]["expected_points"]["found"] / r["checks"]["expected_points"]["total"]
            for r in results if "expected_points" in r["checks"]
        ) / total * 100

        avg_citations = sum(
            r["checks"]["must_cite"]["found"] / r["checks"]["must_cite"]["total"]
            for r in results if "must_cite" in r["checks"]
        ) / total * 100

        print(f"\n平均要点覆盖率: {avg_points:.1f}%")
        print(f"平均来源引用率: {avg_citations:.1f}%")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="评估猴痘问答机器人")
    parser.add_argument("--region", default="中国", help="测试地区")
    parser.add_argument("--limit", type=int, help="限制测试数量")

    args = parser.parse_args()

    run_evaluation(region=args.region, limit=args.limit)
