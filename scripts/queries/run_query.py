#!/usr/bin/env python3
"""
执行 SQL 查询脚本

用法:
    python run_query.py 01_recent_llm_traces
    python run_query.py 02_conversation_messages --conv-id 27
    python run_query.py 03_trace_detail --trace-id xxxxxx
    python run_query.py 04_slow_requests
    python run_query.py 05_list_conversations --user-id 1

或者直接执行所有查询:
    python run_query.py all
"""

import asyncio
import argparse
import re
import sys
from pathlib import Path
from sqlalchemy import text
from aeris.database import get_session_context

QUERIES_DIR = Path(__file__).parent


def read_sql(filename: str) -> str:
    """读取 SQL 文件内容"""
    sql_file = QUERIES_DIR / f"{filename}.sql"
    if not sql_file.exists():
        # 尝试自动补全编号
        for f in QUERIES_DIR.glob(f"*{filename}*.sql"):
            sql_file = f
            break
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL 文件不存在: {filename}")
    return sql_file.read_text()


def substitute_vars(sql: str, **kwargs) -> str:
    """替换 SQL 中的变量"""
    # 替换 -- 注释中的提示
    for key, value in kwargs.items():
        if value is None:
            continue
        # 替换 WHERE 条件中的值
        placeholder = f"-- 替换为你的{key.replace('_', ' ')}"
        sql = sql.replace(placeholder, f"-- 使用值: {value}")

        # 替换具体的变量值
        # 支持格式: key = value, key = 'value', key=?
        patterns = [
            rf"({key})\s*=\s*\d+",  # key = 123
            rf"({key})\s*=\s*'[^']*'",  # key = 'value'
        ]
        for pattern in patterns:
            sql = re.sub(pattern, rf"\1 = {value}" if isinstance(value, int) else rf"\1 = '{value}'", sql)

    return sql


def print_table(headers: list, rows: list, max_width: int = 50) -> None:
    """打印表格"""
    if not rows:
        print("(无数据)")
        return

    # 计算列宽
    col_widths = []
    for i, h in enumerate(headers):
        max_len = len(str(h))
        for row in rows:
            val = str(row[i]) if row[i] is not None else "NULL"
            max_len = max(max_len, len(val[:max_width]))
        col_widths.append(min(max_len + 2, max_width + 2))

    # 打印表头
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print("-" * len(header_line))

    # 打印数据
    for row in rows:
        formatted = []
        for val, width in zip(row, col_widths):
            s = str(val) if val is not None else "NULL"
            if len(s) > max_width:
                s = s[:max_width - 3] + "..."
            formatted.append(s.ljust(width))
        print(" | ".join(formatted))

    print(f"\n共 {len(rows)} 行")


async def execute_query(sql_file: str, **kwargs) -> None:
    """执行单个 SQL 查询"""
    print(f"\n{'='*60}")
    print(f"执行: {sql_file}")
    print('='*60)

    sql = read_sql(sql_file)
    sql = substitute_vars(sql, **kwargs)

    # 提取第一个 SELECT 语句
    select_match = re.search(r'(SELECT\s+.*?)(;|$)', sql, re.DOTALL | re.IGNORECASE)
    if not select_match:
        print("错误: 未找到 SELECT 语句")
        return

    query = select_match.group(1).strip()

    async with get_session_context() as session:
        result = await session.execute(text(query))
        rows = result.fetchall()

        if rows:
            headers = result.keys()
            print_table(headers, rows)
        else:
            print("(无数据)")


async def list_queries() -> None:
    """列出所有可用的查询"""
    print("\n可用查询:\n")
    for sql_file in sorted(QUERIES_DIR.glob("*.sql")):
        content = sql_file.read_text()
        # 提取第一行注释
        first_line = content.split('\n')[0] if content else ""
        desc = first_line.replace('--', '').strip() if first_line.startswith('--') else ""
        print(f"  {sql_file.stem:30} {desc}")
    print()


async def main():
    parser = argparse.ArgumentParser(
        description='执行 SQL 查询脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('query', nargs='?', help='查询名称 (如 01_recent_llm_traces, 或 all 执行全部)')
    parser.add_argument('--conv-id', type=int, help='对话 ID')
    parser.add_argument('--trace-id', type=str, help='Trace ID')
    parser.add_argument('--user-id', type=int, help='用户 ID')
    parser.add_argument('--list', '-l', action='store_true', help='列出可用查询')

    args = parser.parse_args()

    if args.list:
        await list_queries()
        return

    if not args.query:
        parser.print_help()
        return

    if args.query == 'all':
        # 执行所有查询
        for sql_file in sorted(QUERIES_DIR.glob("[0-9]*_*.sql")):
            await execute_query(sql_file.stem)
    else:
        await execute_query(
            args.query,
            conversation_id=args.conv_id,
            trace_id=args.trace_id,
            user_id=args.user_id
        )


if __name__ == '__main__':
    asyncio.run(main())
