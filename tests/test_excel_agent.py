"""测试 Agent 处理 Excel 内容

直接测试 agent_engine.run()，无需网络链路。

用法:
    conda activate aeris
    python tests/test_excel_agent.py
"""

import asyncio
import sys

sys.path.insert(0, "/Users/dykong/Desktop/Aeris")

from meditatio.services.agent_engine import AgentEngine, AgentContext


# 模拟 Excel 内容（Markdown 表格格式）
SAMPLE_EXCEL_CONTENT = """## Sheet: 销售数据

| 日期       | 产品   | 销量 | 单价 | 销售额 |
|:-----------|:-------|-----:|-----:|-------:|
| 2024-01-01 | 笔记本 |  100 | 5000 | 500000 |
| 2024-01-01 | 手机   |  200 | 3000 | 600000 |
| 2024-01-02 | 笔记本 |   80 | 5000 | 400000 |
| 2024-01-02 | 手机   |  150 | 3000 | 450000 |
| 2024-01-03 | 平板   |   50 | 4000 | 200000 |

*... (50 more rows) ...*"""


async def test_excel_analysis():
    """测试 Agent 分析 Excel 内容."""
    print("🧪 测试 Agent 处理 Excel 内容")
    print("-" * 50)

    engine = AgentEngine()
    context = AgentContext(
        user_id=1,
        conversation_id=1,
        max_iterations=5,
    )

    messages = [
        {"role": "system", "content": "你是一个数据分析助手。请分析提供的表格数据。"},
        {"role": "user", "content": f"请分析这个销售数据表格，给出总结和趋势：\n\n{SAMPLE_EXCEL_CONTENT}"}
    ]

    print("📊 模拟 Excel 数据（前200字符）:")
    print(SAMPLE_EXCEL_CONTENT[:200] + "...")
    print(f"\n总计约 {len(SAMPLE_EXCEL_CONTENT)} 字符")
    print("-" * 50)
    print("🤖 Agent 开始处理...\n")

    result = await engine.run(messages, context)

    print(f"📝 AI 回复:\n{result.content}\n")
    print(f"📈 Tokens: ↑{result.usage['input_tokens']} ↓{result.usage['output_tokens']}")
    print(f"⏱️  延迟: {result.latency_ms}ms")
    print(f"🔄 轮次: {result.iterations}")

    if result.error:
        print(f"❌ 错误: {result.error}")

    return result


async def test_image_base64():
    """测试 Agent 处理图片（模拟 base64）."""
    print("\n🧪 测试 Agent 处理图片")
    print("-" * 50)

    # 模拟一个小图片的 base64
    fake_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    engine = AgentEngine()
    context = AgentContext(user_id=1, conversation_id=2, max_iterations=5)

    messages = [
        {"role": "system", "content": "你是一个图像分析助手。"},
        {"role": "user", "content": [
            {"type": "text", "text": "请描述这张图片"},
            {"type": "image_url", "image_url": {"url": fake_base64}}
        ]}
    ]

    print("🖼️  图片 base64 前缀:", fake_base64[:50], "...")
    print("-" * 50)
    print("🤖 Agent 开始处理...\n")

    result = await engine.run(messages, context)

    print(f"📝 AI 回复:\n{result.content}\n")
    print(f"📈 Tokens: ↑{result.usage['input_tokens']} ↓{result.usage['output_tokens']}")

    return result


if __name__ == "__main__":
    # 运行测试
    print("=" * 60)
    print("Agent Excel/文件处理测试")
    print("=" * 60)

    try:
        asyncio.run(test_excel_analysis())
    except Exception as e:
        print(f"❌ Excel 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
