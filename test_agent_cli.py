"""独立 Agent CLI 测试脚本

使用方法:
    python test_agent_cli.py

前提:
    1. 需要有 LLM 服务在运行 (如 SGLang: http://localhost:30000/v1)
    2. 在项目根目录下运行
    3. 已激活 aeris 环境
"""

import asyncio
import sys

# 添加项目路径
sys.path.insert(0, "/Users/dykong/Desktop/Aeris")

from aeris.services.agent_engine import AgentEngine, AgentContext


async def main():
    """简单的 Agent 对话循环."""
    print("🤖 Agent CLI 测试工具")
    print("-" * 40)
    print("配置: 默认 Provider (SGLang @ localhost:30000/v1)")
    print("指令: exit / quit 退出, clear 清空对话")
    print("-" * 40)
    print()

    # 初始化 Agent
    engine = AgentEngine()
    context = AgentContext(
        user_id=1,
        conversation_id=1,
        max_iterations=10,
    )

    # 对话历史
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."}
    ]

    try:
        while True:
            # 用户输入
            try:
                user_input = input("👤 You: ")
            except EOFError:
                print()
                break

            # 空输入
            if not user_input.strip():
                continue

            # 退出指令
            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 Goodbye!")
                break

            # 清空对话
            if user_input.lower() == "clear":
                messages = [messages[0]]  # 保留 system
                context.iteration_count = 0
                context.total_input_tokens = 0
                context.total_output_tokens = 0
                print("🗑️  对话已清空\n")
                continue

            # 添加到历史
            messages.append({"role": "user", "content": user_input})

            # 调用 Agent
            print("🤖 Agent: ", end="", flush=True)

            try:
                result = await engine.run(messages, context)

                if result.error:
                    print(f"[错误: {result.error}]")
                elif result.content:
                    print(result.content)
                else:
                    print("[无回复]")

                # 显示统计
                print(
                    f"\n   [Tokens: ↑{result.usage['input_tokens']} ↓{result.usage['output_tokens']} | "
                    f"轮次: {result.iterations} | 延迟: {result.latency_ms}ms]"
                )

                # 把 AI 回复加入历史
                if result.content:
                    messages.append({
                        "role": "assistant",
                        "content": result.content
                    })

            except Exception as e:
                print(f"[调用失败: {e}]")

            print()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")


if __name__ == "__main__":
    # asyncio.run 创建事件循环并运行 main()
    asyncio.run(main())
