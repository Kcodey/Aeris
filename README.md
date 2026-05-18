# Meditatio

在 OpenClaw/Hermes 架构基础上增加本地用户认证与数据隔离的轻量级 AI Agent 平台。

## 核心特性

- **用户认证**：基于 JWT 的注册/登录系统，支持多用户数据隔离
- **实时对话**：WebSocket 流式输出，支持 AI 思考状态指示
- **对话管理**：侧边栏按时间分组（今天/昨天/本周/更早），支持消息预览、手动编辑标题、删除对话
- **Agent Loop**：完整的对话循环，支持工具调用和流式输出
- **文件系统**：文件上传下载、图片预览、缩略图生成，支持图片随消息发送
- **定时任务**：支持 Cron/一次性/间隔触发，Agent 可自主创建任务
- **监控仪表板**：LLM Trace 采集、Token 用量趋势、模型分布饼图、延迟分布、调用记录详情

## 技术栈

**后端**：Python 3.11+, FastAPI, SQLModel, PostgreSQL, APScheduler
**前端**：React 18, TypeScript, Vite, Tailwind CSS, Ant Design 5.x, Lucide React, React Markdown, Recharts
**AI**：SGLang / OpenAI 兼容接口

## 系统要求

- Python >= 3.11
- Node.js >= 18
- PostgreSQL 14+
- libmagic（文件 MIME 检测，macOS: `brew install libmagic`）

## 快速开始

### 1. 环境配置

```bash
# 克隆项目
git clone https://github.com/Kcodey/Meditatio.git
cd Meditatio

# 创建并激活 Python 环境
conda create -n meditatio python=3.11
conda activate meditatio

# 安装依赖
pip install -e ".[dev]"

# 安装前端依赖
cd frontend
npm install
```

### 2. 数据库启动

```bash
# 启动 PostgreSQL
docker-compose up -d db
```

### 3. 环境变量

```bash
cp .env.example .env
```

关键配置项说明：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql://skdy:skdy@localhost:5432/meditatio` |
| `SECRET_KEY` | JWT 签名密钥（生产环境务必修改） | `your-secret-key` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 登录 Token 有效期（分钟） | `1440` |
| `SGLANG_BASE_URL` | LLM 服务地址 | `http://localhost:30000/v1` |
| `SGLANG_MODEL` | 模型名称 | `default` |

### 4. 启动服务

```bash
# 后端（端口 8000）
uvicorn meditatio.main:app --reload

# 前端（新终端，端口 3000）
cd frontend
npm run dev
```

访问 http://localhost:3000

> 前端通过 Vite 代理将 `/api` 和 `/ws` 请求转发到后端 `localhost:8000`。

## 开发命令

```bash
# 运行测试
pytest tests/ -v

# 代码检查
black meditatio/ tests/
isort meditatio/ tests/
```

## API 概览

| 端点 | 说明 |
|------|------|
| `POST /api/v1/auth/register` | 用户注册 |
| `POST /api/v1/auth/login` | 用户登录 |
| `GET /api/v1/conversations` | 列出对话 |
| `POST /api/v1/conversations` | 创建对话 |
| `PATCH /api/v1/conversations/{id}` | 更新对话标题 |
| `DELETE /api/v1/conversations/{id}` | 删除对话 |
| `POST /api/v1/conversations/{id}/messages` | 发送消息（非流式） |
| `WS /ws/chat` | WebSocket 实时对话（流式） |
| `GET /api/v1/monitoring/dashboard` | 监控仪表盘数据 |
| `GET /api/v1/monitoring/traces` | LLM Trace 列表 |

## 项目结构

```
meditatio/
├── main.py                 # FastAPI 入口
├── config.py               # Pydantic 配置
├── database.py             # Async SQLAlchemy / SQLModel
├── models/                 # 数据库模型（User, Conversation, Message, Trace, Task）
├── routers/                # API 路由（auth, chat, files, tasks, monitoring, websocket）
├── services/               # 业务逻辑（chat, file, agent engine, provider, monitoring）
├── schemas/                # Pydantic 请求/响应模型
├── tools/                  # Agent 工具注册与执行
└── utils/                  # 安全、文件等工具函数

frontend/
├── src/
│   ├── main.tsx            # React 入口
│   ├── App.tsx             # 根组件（路由配置）
│   ├── global.css          # Tailwind 入口 + 全局样式
│   ├── pages/              # 页面（ChatPage, MonitoringPage）
│   ├── components/         # 业务组件
│   │   ├── Chat/           # 聊天相关（ChatWindow, MessageBubble, ChatInput, EmptyState）
│   │   ├── Layout/         # 布局（AppLayout, Sidebar）
│   │   └── Monitoring/     # 监控图表（StatCard, TokenTrendChart, ModelPieChart, LatencyBarChart）
│   ├── services/           # API 服务（chat, file, monitoring）
│   ├── types/              # TypeScript 类型定义
│   └── utils/              # 工具函数（token 管理）
└── package.json
```

## 许可证

MIT
