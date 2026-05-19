"""Bash execution tool for agent."""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict

from meditatio.tools.base import Tool, ToolParameter, ToolResult


# 危险命令黑名单（正则）
DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+[/.*]+',                    # rm -rf / 或 rm -rf ./*
    r'curl\s+.*\|\s*bash',                   # curl ... | bash
    r'wget\s+.*\|\s*bash',                   # wget ... | bash
    r'yum\s+.*\|\s*bash',                    # yum ... | bash
    r'apt\s+.*\|\s*bash',                    # apt ... | bash
    r'shutdown',                              # 关机
    r'reboot',                                # 重启
    r'halt',                                  # 停止
    r'dd\s+',                                 # 磁盘操作
    r'mkfs',                                  # 格式化
    r':\(\)\{:\|:&\};:',                     # fork bomb
    r'\.\.\/',                                # 目录穿越
    r'>\s*/dev/sd[a-z]',                     # 直接写磁盘
    r'chmod\s+-R\s+777',                     # 权限放大
    r'passwd',                               # 修改密码
    r'su\s+',                                 # 切换用户
    r'sudo\s+',                              # 提权
    r'eval\s+',                              # eval 动态执行
    r'exec\s+',                              # exec 替换进程
    r'nc\s+.*-e\s+',                         # nc 反向shell
    r'bash\s+-i',                            # 交互式bash
    r'/proc/',                               # 访问 /proc
    r'sysctl',                               # 修改内核参数
    r'mount\s+',                             # 挂载
    r'umount\s+',                            # 卸载
]


class BashTool(Tool):
    """Execute bash commands with security restrictions."""

    name = "bash"
    description = (
        "Execute a bash command. "
        "Useful for: running pandoc, libreoffice, pdftoppm, or other CLI tools. "
        "Working directory is the project root. "
        "Dangerous commands are blocked."
    )
    parameters = [
        ToolParameter(
            name="command",
            type="string",
            description="Bash command to execute",
            required=True,
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Timeout in seconds (default: 30)",
            required=False,
        ),
    ]

    def _check_command(self, command: str) -> tuple[bool, str]:
        """检查命令是否安全"""
        # 检查危险模式
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"危险命令被拦截: 匹配到禁止模式 '{pattern}'"

        # 检查是否在允许的目录内（项目目录）
        project_root = Path(__file__).parent.parent.parent
        command_lower = command.lower()

        # 禁止访问项目目录之外的路径
        forbidden_dirs = ['/etc/', '/var/', '/usr/', '/bin/', '/sbin/', '/boot/', '/sys/', '/proc/', '/root/', '/home/']
        for forbidden_dir in forbidden_dirs:
            if forbidden_dir in command and 'cd' in command_lower:
                # 允许 cd 进入项目子目录，但禁止 cd 到外部
                if not command.strip().startswith('cd') or command.count('..') > 0:
                    return False, f"禁止访问项目目录之外的路径"

        return True, ""

    async def execute(
        self,
        command: str,
        timeout: int = 30,
        _context: Dict = None,
    ) -> ToolResult:
        # 安全检查
        is_safe, error_msg = self._check_command(command)
        if not is_safe:
            return ToolResult(
                success=False,
                data=None,
                error=f"命令安全检查失败: {error_msg}",
            )

        try:
            # Use project root as working directory
            project_root = Path(__file__).parent.parent.parent
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root),
            )

            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"

            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    data={"output": output, "returncode": result.returncode},
                    error=f"Command failed with exit code {result.returncode}",
                )

            return ToolResult(
                success=True,
                data={"output": output, "returncode": result.returncode},
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))


def register_bash_tool(registry):
    """Register bash tool."""
    registry.register(BashTool())
