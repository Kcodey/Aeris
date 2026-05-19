"""独立 Agent CLI 测试脚本（支持文件上传）

使用方法:
    python test_agent_cli.py

前提:
    1. 需要有 LLM 服务在运行 (如 SGLang: http://localhost:30000/v1)
    2. 在项目根目录下运行
    3. 已激活 aeris 环境
    4. 已配置数据库连接 (DATABASE_URL)

指令:
    exit/quit/q    - 退出
    clear          - 清空对话历史
    /file <path>   - 上传并分析文件 (支持 Excel、图片、文本等)
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, "/Users/dykong/Desktop/Aeris")

from meditatio.services.agent_engine import AgentEngine, AgentContext
from meditatio.services.file_service import FileService
from meditatio.database import get_session_context


async def upload_and_read_file(file_path: str, user_id: int = 1) -> tuple:
    """上传文件并读取内容。

    Returns: (file_name, content, mime_type)
    """
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if not path.is_file():
        raise ValueError(f"路径不是文件: {file_path}")

    async with get_session_context() as session:
        file_service = FileService(session)

        # 读取文件内容
        with open(path, "rb") as f:
            file_data = f.read()

        # 检测 MIME 类型
        import mimetypes
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

        # 保存文件
        file_record = await file_service.save_file(
            user_id=user_id,
            original_name=path.name,
            content_type=content_type,
            file_data=file_data,
            conversation_id=None,
        )

        # 读取文件内容（转换为 LLM 可用格式）
        content = await file_service.read_file_content(file_record)

        return file_record.original_name, content, file_record.mime_type, file_record.id


async def main():
    """支持文件上传的 Agent 对话循环."""
    print("🤖 Agent CLI 测试工具（支持文件上传）")
    print("-" * 50)
    print("配置: 默认 Provider (SGLang @ localhost:30000/v1)")
    print("指令: exit/quit/q 退出 | clear 清空 | /file <路径> 上传文件")
    print("-" * 50)
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

            # 文件上传指令: /file path/to/file
            if user_input.startswith("/file "):
                file_path = user_input[6:].strip()
                if not file_path:
                    print("❌ 请提供文件路径，例如: /file ~/Documents/data.xlsx")
                    continue

                try:
                    print(f"📁 正在上传: {file_path} ...", end=" ", flush=True)
                    file_name, content, mime_type, file_id = await upload_and_read_file(file_path)
                    print(f"✅ (ID: {file_id})")

                    # 显示文件类型和内容预览
                    if mime_type.startswith("image/"):
                        print(f"🖼️  图片文件，已转换为 base64 (前100字符): {content[:100]}...")
                        # 图片直接作为 user message 的 content
                        user_content = [
                            {"type": "text", "text": f"请分析这张图片 ({file_name}):"},
                            {"type": "image_url", "image_url": {"url": content}},
                        ]
                    else:
                        # 文本/Excel 等，截断预览
                        preview = content[:500]
                        if len(content) > 500:
                            preview += f"\n... (共 {len(content)} 字符，已截断)"
                        print(f"📝 文件内容预览:\n{preview}\n")

                        # 询问用户要发送给 AI 的提示
                        follow_up = input("💬 要对文件做什么操作？(直接回车使用默认分析，或输入自定义问题): ").strip()
                        if not follow_up:
                            follow_up = f"请分析这个文件: {file_name}"

                        user_content = [
                            {"type": "text", "text": f"{follow_up}\n\n[文件内容]\n{content[:8000]}"}
                        ]

                    # 添加到历史（OpenAI 格式）
                    messages.append({"role": "user", "content": user_content})

                except FileNotFoundError as e:
                    print(f"\n❌ {e}")
                    continue
                except ValueError as e:
                    print(f"\n❌ {e}")
                    continue
                except Exception as e:
                    print(f"\n❌ 处理文件失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            else:
                # 普通文本消息
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
                import traceback
                traceback.print_exc()

            print()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
