# Aeris

在 OpenClaw/Hermes 架构基础上增加本地用户认证与数据隔离的轻量级 AI Agent 平台。

## 核心特性

- **用户认证**：基于 JWT 的注册/登录系统，支持多用户数据隔离
- **Agent Loop**：完整的对话循环，支持工具调用和流式输出
- **文件系统**：文件上传下载、图片预览、缩略图生成
- **定时任务**：支持 Cron/一次性/间隔触发，Agent 可自主创建任务
- **监控仪表板**：LLM Trace 采集、Token 用量统计、延迟分析

## 技术栈

**后端**：Python 3.11+, FastAPI, SQLModel, PostgreSQL, APScheduler
**前端**：React 18, TypeScript, Ant Design 5.x, @ant-design/x
**AI**：SGLang/OpenAI 兼容接口

## 快速开始

### 1. 环境配置

```bash
# 克隆项目
git clone https://github.com/Kcodey/Aeris.git
cd Aeris

# 创建并激活环境
conda create -n aeris python=3.11
conda activate aeris

# 安装依赖
pip install -e ".[dev]"
```

### 2. 数据库启动

```bash
# 启动 PostgreSQL
docker-compose up -d db
```

### 3. 环境变量

```bash
cp .env.example .env
# 编辑 .env 配置数据库和 LLM 服务地址
```

### 4. 启动服务

```bash
# 后端
uvicorn aeris.main:app --reload

# 前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 开发命令

```bash
# 运行测试
pytest tests/ -v

# 代码检查
black aeris/ tests/
isort aeris/ tests/
```

## 项目结构

```
aeris/
├── main.py              # FastAPI 入口
├── routers/             # API 路由
├── services/            # 业务逻辑
├── models/              # 数据库模型
├── tools/               # Agent 工具
└── utils/               # 工具函数

frontend/
├── src/
│   ├── pages/           # 页面组件
│   ├── components/      # 业务组件
│   ├── services/        # API 服务
│   └── types/           # TypeScript 类型
└── package.json
```

## 许可证

MIT
