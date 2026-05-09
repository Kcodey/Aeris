# 开发调试 SQL

存放开发时用的查询脚本。

## 使用方式

### 推荐：Python 脚本（自动连接数据库）

```bash
# 先激活环境
conda activate aeris

# 查看可用查询
python scripts/queries/run_query.py -l

# 执行查询（支持模糊匹配）
python scripts/queries/run_query.py 01_recent_llm_traces
python scripts/queries/run_query.py 01  # 简写也能匹配

# 带参数查询
python scripts/queries/run_query.py 02_conversation_messages --conv-id 27
python scripts/queries/run_query.py 03_trace_detail --trace-id your-trace-id
python scripts/queries/run_query.py 05_list_conversations --user-id 1

# 执行所有查询
python scripts/queries/run_query.py all
```

### 命令行（需要 psql）

```bash
# 执行单个 SQL
psql postgresql://aeris:aeris@localhost:5432/aeris -f 01_recent_llm_traces.sql

# 或者交互式
psql postgresql://aeris:aeris@localhost:5432/aeris
\i 01_recent_llm_traces.sql
```

### Python（异步，用于代码中）

```python
import asyncio
from aeris.database import get_session_context
from sqlalchemy import text

async def query():
    async with get_session_context() as session:
        result = await session.execute(text("SELECT * FROM llm_traces LIMIT 5"))
        for row in result:
            print(row)

asyncio.run(query())
```

## 文件说明

| 文件 | 用途 |
|:---|:---|
| 01_recent_llm_traces.sql | 最近 10 次模型调用 |
| 02_conversation_messages.sql | 查看对话消息历史 |
| 03_trace_detail.sql | 单次调用完整输入输出 |
| 04_slow_requests.sql | 慢请求（>3秒） |
| 05_list_conversations.sql | 查看所有对话及其 ID |
| 06_skill_usage_stats.sql | 技能使用统计 |

## 新增查询

复制模板，按需修改：

```sql
-- 文件名：05_your_query.sql
-- 用途：描述

SELECT * FROM your_table WHERE ...;
```
