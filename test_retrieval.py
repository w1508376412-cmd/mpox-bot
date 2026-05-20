"""测试数据库检索功能"""
import sys
sys.path.insert(0, '/Users/yanfei/Library/Application Support/0011/workspaces/default/mpox-bot/backend')

from retriever import search_chunks

try:
    print("测试检索功能...")
    results = search_chunks("猴痘是什么？", region="中国", top_k=3)

    print(f"\n找到 {len(results)} 个结果：")
    for i, result in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"  来源: {result['source']}")
        print(f"  内容: {result['content'][:100]}...")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
