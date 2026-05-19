# 重命名 Aeris 为 Meditatio 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 将项目中的 `aeris` 目录和包名全部替换为 `meditatio`，同时更新所有相关配置文件。

**架构：** 分为 8 个独立步骤，每步验证后再进行下一步。目录重命名与导入替换分开，便于回滚。

**涉及：** 约 330 处引用，包括 Python 源码、配置文件、文档。

---

## 步骤概览

| 步骤 | 内容 | 风险 | 提交 |
|------|------|------|------|
| 1 | 更新 `pyproject.toml` 包名 | 低 | 独立提交 |
| 2 | 更新 `docker-compose.yml` | 低 | 独立提交 |
| 3 | 更新 `alembic/env.py` | 低 | 独立提交 |
| 4 | 更新 `CLAUDE.md` 和 `.env.example` | 低 | 独立提交 |
| 5 | **git mv aeris meditatio** | 中 | 独立提交 |
| 6 | 批量替换所有 `from aeris.` | 中 | 独立提交 |
| 7 | 更新 `run.py` 和测试脚本 | 低 | 独立提交 |
| 8 | 验证服务启动 | - | 最终提交 |

---

## Task 1: 更新 pyproject.toml

**Files:**
- Modify: `pyproject.toml:6-13`

- [ ] **Step 1: 更新包名**

```toml
[project]
name = "meditatio"
version = "0.1.0"
description = "A lightweight AI Agent platform"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Meditatio Team"}
]
```

- [ ] **Step 2: 验证**

```bash
grep "name = " pyproject.toml
```

预期：`name = "meditatio"`

- [ ] **Step 3: 提交**

```bash
git add pyproject.toml && git commit -m "refactor: rename package to meditatio in pyproject.toml"
```

---

## Task 2: 更新 docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 检查当前内容**

```bash
grep -n "aeris" docker-compose.yml
```

预期输出类似：
- 可能有 `MEDITATIO_ENV` 或类似的容器名称前缀
- `image: aeris-app` → `image: meditatio-app`
- 服务名 `aeris` → `meditatio`

- [ ] **Step 2: 更新容器名称和服务名**

```yaml
services:
  meditatio:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - MEDITATIO_ENV=development
```

- [ ] **Step 3: 提交**

```bash
git add docker-compose.yml && git commit -m "refactor: rename service to meditatio in docker-compose.yml"
```

---

## Task 3: 更新 alembic/env.py

**Files:**
- Modify: `alembic/env.py:10-12`

- [ ] **Step 1: 检查当前内容**

```bash
grep -n "aeris" alembic/env.py
```

预期输出：
```
10:from aeris.config import get_settings
11:from aeris.models import SQLModel
12:from aeris.models import User, Conversation, Message, ScheduledTask, FileRecord, LLMTrace, KnowledgeBase, Document, Chunk
```

- [ ] **Step 2: 更新导入**

```python
from meditatio.config import get_settings
from meditatio.models import SQLModel
from meditatio.models import User, Conversation, Message, ScheduledTask, FileRecord, LLMTrace, KnowledgeBase, Document, Chunk
```

- [ ] **Step 3: 验证**

```bash
grep -c "from aeris" alembic/env.py
```

预期：`0`

- [ ] **Step 4: 提交**

```bash
git add alembic/env.py && git commit -m "refactor: update alembic imports to meditatio"
```

---

## Task 4: 更新文档文件

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.env.example`（如果存在）

- [ ] **Step 1: 检查 CLAUDE.md**

```bash
grep -n "aeris" CLAUDE.md
```

预期：项目结构中的 `aeris/` 目录名

- [ ] **Step 2: 更新 CLAUDE.md**

将项目结构中的 `aeris/` 替换为 `meditatio/`

```markdown
meditatio/
├── main.py                 # FastAPI 入口
├── config.py               # Pydantic 配置
...
```

- [ ] **Step 3: 检查 .env.example**

```bash
grep -n "aeris" .env.example 2>/dev/null || echo "文件不存在或无需修改"
```

- [ ] **Step 4: 提交**

```bash
git add CLAUDE.md .env.example 2>/dev/null
git commit -m "docs: update project name in CLAUDE.md"
```

---

## Task 5: 重命名目录（关键步骤）

**Files:**
- Modify: `aeris/` → `meditatio/` (目录重命名)

**风险：此步骤之后目录结构发生变化，后续步骤必须在此基础上执行。**

- [ ] **Step 1: 使用 git mv 重命名目录**

```bash
git mv aeris meditatio
```

- [ ] **Step 2: 验证目录已重命名**

```bash
ls -la meditatio/
```

预期：可以看到 meditatio 目录下的所有文件

- [ ] **Step 3: 验证旧目录不存在**

```bash
test -d aeris && echo "ERROR: 目录仍存在" || echo "✅ aeris 目录已删除"
```

- [ ] **Step 4: 提交**

```bash
git commit -m "refactor: rename aeris directory to meditatio"
```

---

## Task 6: 批量更新所有 Python 导入（关键步骤）

**Files:**
- Modify: 所有 `meditatio/` 目录下的 `.py` 文件（约 50 个文件，220 处引用）

**风险：此步骤涉及所有 Python 文件的导入替换。**

- [ ] **Step 1: 批量替换导入语句**

```bash
# 替换 from aeris. 为 from meditatio.
find meditatio -name "*.py" -type f | xargs sed -i 's/from aeris\./from meditatio./g'

# 替换 import aeris 为 import meditatio
find meditatio -name "*.py" -type f | xargs sed -i 's/import aeris/import meditatio/g'
```

- [ ] **Step 2: 验证无遗漏**

```bash
grep -r "from aeris" meditatio/ --include="*.py" | wc -l
grep -r "import aeris" meditatio/ --include="*.py" | wc -l
```

预期：两个结果都为 `0`

- [ ] **Step 3: 验证导入可以正常解析**

```bash
conda activate meditatio
cd /home/skdy/server/Aeris
python -c "from meditatio.main import app; print('✅ 导入成功')"
```

预期：输出 `✅ 导入成功`

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "refactor: update all imports from aeris to meditatio"
```

---

## Task 7: 更新根目录文件和测试脚本

**Files:**
- Modify: `run.py`
- Modify: `tests/` 目录下的测试文件

- [ ] **Step 1: 检查 run.py**

```bash
grep -n "aeris" run.py 2>/dev/null || echo "无需修改或文件不存在"
```

- [ ] **Step 2: 检查测试文件**

```bash
grep -rn "aeris" tests/ --include="*.py" | head -20
```

预期：测试文件中的 import 语句

- [ ] **Step 3: 更新测试文件中的导入**

```bash
find tests -name "*.py" | xargs sed -i 's/from aeris\./from meditatio./g'
find tests -name "*.py" | xargs sed -i 's/import aeris/import meditatio/g'
```

- [ ] **Step 4: 验证**

```bash
grep -r "from aeris" tests/ --include="*.py" | wc -l
```

预期：`0`

- [ ] **Step 5: 提交**

```bash
git add tests/ run.py 2>/dev/null
git commit -m "refactor: update test imports and run.py"
```

---

## Task 8: 验证服务启动

**Files:**
- None (验证步骤)

- [ ] **Step 1: 验证后端可以导入**

```bash
conda activate meditatio
python -c "from meditatio.main import app; print('✅ 主模块导入成功')"
python -c "from meditatio.config import get_settings; print('✅ 配置导入成功')"
python -c "from meditatio.database import get_session; print('✅ 数据库模块导入成功')"
```

- [ ] **Step 2: 运行测试**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

预期：测试通过或仅有与改名无关的失败

- [ ] **Step 3: 验证前端可以构建**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

预期：构建成功

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "test: verify meditatio rename works correctly"
```

---

## 回滚方案

如果步骤 5 或 6 出问题：

```bash
# 回滚到步骤 5 之前
git reset --hard HEAD~1
git mv meditatio aeris

# 回滚到步骤 6 之后（步骤 5 之后的提交）
git reset --hard HEAD~1
# 然后重新执行步骤 6
```

---

## 执行选项

**1. Subagent-Driven (recommended)** - 每个任务派发一个 subagent，任务间审查，快速迭代

**2. Inline Execution** - 使用 executing-plans 在本会话中批量执行，带检查点

**选择哪个方式？**