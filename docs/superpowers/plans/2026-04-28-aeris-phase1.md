# Aeris Phase 1 - 项目骨架、数据库与认证 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 搭建 Aeris 后端项目骨架，配置 PostgreSQL 数据库，实现基于 JWT 的用户认证系统，提供基础 API 框架。

**架构：** 单体 FastAPI 应用，SQLModel ORM，PostgreSQL 持久化，Pydantic Settings 配置管理，Docker Compose 本地开发环境。

**技术栈：** Python 3.11+, FastAPI, SQLModel, PostgreSQL 16, Pydantic Settings, PyJWT, Passlib (bcrypt), Alembic (数据库迁移)

---

## 文件结构

```
aeris/
├── pyproject.toml              # 项目配置、依赖
├── .env.example                # 环境变量示例
├── .gitignore                  # Git 忽略规则
├── docker-compose.yml          # 本地开发环境
├── Dockerfile                  # 生产镜像
├── README.md                   # 项目说明
├── aeris/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # Pydantic Settings 配置
│   ├── database.py             # 数据库连接、Session 管理
│   ├── models/
│   │   ├── __init__.py         # 模型导出
│   │   ├── base.py             # 基础模型、时间戳混入
│   │   ├── user.py             # User 模型
│   │   ├── conversation.py     # Conversation 模型
│   │   ├── message.py          # Message 模型
│   │   ├── scheduled_task.py   # ScheduledTask 模型
│   │   ├── file_record.py      # FileRecord 模型
│   │   └── trace.py            # LLMTrace 模型
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证路由（注册/登录）
│   │   └── health.py           # 健康检查
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py     # 认证业务逻辑
│   └── utils/
│       ├── __init__.py
│       └── security.py         # JWT、密码哈希工具
├── alembic/
│   ├── env.py                  # Alembic 环境配置
│   ├── script.py.mako          # 迁移脚本模板
│   └── versions/               # 迁移版本目录
└── tests/
    ├── __init__.py
    ├── conftest.py             # pytest 配置、fixtures
    └── test_auth.py            # 认证测试
```

---

## 任务分解

### 任务 1：项目初始化与依赖配置

**文件：**
- 创建：`pyproject.toml`
- 创建：`.gitignore`
- 创建：`.env.example`
- 创建：`README.md`

- [ ] **步骤 1：创建 pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "aeris"
version = "0.1.0"
description = "A lightweight AI Agent platform"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Aeris Team"}
]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "sqlmodel>=0.0.14",
    "psycopg[binary]>=3.1.18",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "alembic>=1.13.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
]

[tool.hatch.build.targets.wheel]
packages = ["aeris"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **步骤 2：创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# Docker volumes
postgres_data/

# Logs
*.log

# Testing
.coverage
htmlcov/
.pytest_cache/
```

- [ ] **步骤 3：创建 .env.example**

```bash
# Database
DATABASE_URL=postgresql://aeris:aeris@localhost:5432/aeris

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# App
APP_NAME=Aeris
DEBUG=true
```

- [ ] **步骤 4：创建 README.md**

```markdown
# Aeris

A lightweight AI Agent platform.

## Development Setup

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start PostgreSQL:
```bash
docker-compose up -d db
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start development server:
```bash
uvicorn aeris.main:app --reload
```

## Testing

```bash
pytest
```
```

- [ ] **步骤 5：Commit**

```bash
git add pyproject.toml .gitignore .env.example README.md
git commit -m "chore: initialize project with dependencies"
```

---

### 任务 2：Docker Compose 配置

**文件：**
- 创建：`docker-compose.yml`
- 创建：`Dockerfile`

- [ ] **步骤 1：创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: aeris
      POSTGRES_PASSWORD: aeris
      POSTGRES_DB: aeris
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aeris"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://aeris:aeris@db:5432/aeris
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./aeris:/app/aeris
      - uploads:/app/uploads
    command: uvicorn aeris.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
  uploads:
```

- [ ] **步骤 2：创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY aeris/ ./aeris/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create uploads directory
RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "aeris.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **步骤 3：Commit**

```bash
git add docker-compose.yml Dockerfile
git commit -m "chore: add docker compose and dockerfile"
```

---

### 任务 3：基础配置模块

**文件：**
- 创建：`aeris/__init__.py`
- 创建：`aeris/config.py`

- [ ] **步骤 1：创建 aeris/__init__.py**

```python
"""Aeris - A lightweight AI Agent platform."""

__version__ = "0.1.0"
```

- [ ] **步骤 2：创建 aeris/config.py**

```python
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "Aeris"
    debug: bool = False
    version: str = "0.1.0"

    # Database
    database_url: str = "postgresql://aeris:aeris@localhost:5432/aeris"

    # Security
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Storage
    uploads_dir: str = "./uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/__init__.py aeris/config.py
git commit -m "feat: add pydantic settings configuration"
```

---

### 任务 4：数据库模块

**文件：**
- 创建：`aeris/database.py`
- 创建：`aeris/models/__init__.py`
- 创建：`aeris/models/base.py`

- [ ] **步骤 1：创建 aeris/database.py**

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from aeris.config import get_settings

settings = get_settings()

# Convert postgresql:// to postgresql+asyncpg:// for async support
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    async_database_url = database_url

engine = create_async_engine(
    async_database_url,
    echo=settings.debug,
    future=True,
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

- [ ] **步骤 2：创建 aeris/models/__init__.py**

```python
"""SQLModel database models."""

from aeris.models.base import TimestampMixin
from aeris.models.user import User
from aeris.models.conversation import Conversation
from aeris.models.message import Message
from aeris.models.scheduled_task import ScheduledTask
from aeris.models.file_record import FileRecord
from aeris.models.trace import LLMTrace

__all__ = [
    "TimestampMixin",
    "User",
    "Conversation",
    "Message",
    "ScheduledTask",
    "FileRecord",
    "LLMTrace",
]
```

- [ ] **步骤 3：创建 aeris/models/base.py**

```python
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TimestampMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
```

- [ ] **步骤 4：Commit**

```bash
git add aeris/database.py aeris/models/__init__.py aeris/models/base.py
git commit -m "feat: add database module with async SQLAlchemy"
```

---

### 任务 5：用户模型

**文件：**
- 创建：`aeris/models/user.py`

- [ ] **步骤 1：创建 aeris/models/user.py**

```python
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlmodel import SQLModel, Field, Relationship

from aeris.models.base import TimestampMixin

if TYPE_CHECKING:
    from aeris.models.conversation import Conversation
    from aeris.models.scheduled_task import ScheduledTask
    from aeris.models.file_record import FileRecord


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)

    # Quota for future multi-tenant expansion
    quota_tokens_daily: Optional[int] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    conversations: List["Conversation"] = Relationship(back_populates="user")
    tasks: List["ScheduledTask"] = Relationship(back_populates="user")
    files: List["FileRecord"] = Relationship(back_populates="user")
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/models/user.py
git commit -m "feat: add user model"
```

---

### 任务 6：Conversation 和 Message 模型

**文件：**
- 创建：`aeris/models/conversation.py`
- 创建：`aeris/models/message.py`

- [ ] **步骤 1：创建 aeris/models/conversation.py**

```python
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.user import User
    from aeris.models.message import Message


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: Optional[str] = Field(default=None, max_length=200)
    status: str = Field(default="active")  # active, archived, deleted

    # Model config snapshot for this conversation
    model_config_snapshot: Optional[dict] = Field(
        default=None, sa_column=Column(JSON)
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")
```

- [ ] **步骤 2：创建 aeris/models/message.py**

```python
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.conversation import Conversation


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    role: str = Field(max_length=20)  # system, user, assistant, tool
    content: Optional[str] = Field(default=None)

    # Tool calls
    tool_calls: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    tool_call_id: Optional[str] = Field(default=None, max_length=100)

    # Token usage for monitoring
    input_tokens: Optional[int] = Field(default=None)
    output_tokens: Optional[int] = Field(default=None)
    tokens_estimated: bool = Field(default=False)

    # Trace for debugging
    trace_id: Optional[str] = Field(default=None, index=True, max_length=100)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/models/conversation.py aeris/models/message.py
git commit -m "feat: add conversation and message models"
```

---

### 任务 7：ScheduledTask 和 FileRecord 模型

**文件：**
- 创建：`aeris/models/scheduled_task.py`
- 创建：`aeris/models/file_record.py`

- [ ] **步骤 1：创建 aeris/models/scheduled_task.py**

```python
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.user import User


class ScheduledTask(SQLModel, table=True):
    __tablename__ = "scheduled_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)

    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None)

    # Trigger configuration
    trigger_type: str = Field(max_length=20)  # cron, once, interval
    trigger_config: dict = Field(sa_column=Column(JSON))

    # Task payload (what to execute)
    task_payload: dict = Field(sa_column=Column(JSON))

    # Status
    status: str = Field(default="pending")  # pending, running, completed, failed, cancelled

    # Execution tracking
    last_run_at: Optional[datetime] = Field(default=None)
    last_result: Optional[str] = Field(default=None)
    next_run_at: Optional[datetime] = Field(default=None, index=True)
    run_count: int = Field(default=0)

    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="tasks")
```

- [ ] **步骤 2：创建 aeris/models/file_record.py**

```python
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from aeris.models.user import User


class FileRecord(SQLModel, table=True):
    __tablename__ = "file_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: Optional[int] = Field(
        foreign_key="conversations.id", default=None, index=True
    )

    # File metadata
    original_name: str = Field(max_length=255)
    stored_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size_bytes: int
    storage_path: str = Field(max_length=500)

    # Processing status
    status: str = Field(default="ready")  # uploading, processing, ready, error
    extracted_text: Optional[str] = Field(default=None)

    # Access control
    is_public: bool = Field(default=False)
    expires_at: Optional[datetime] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: Optional["User"] = Relationship(back_populates="files")
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/models/scheduled_task.py aeris/models/file_record.py
git commit -m "feat: add scheduled_task and file_record models"
```

---

### 任务 8：LLMTrace 模型

**文件：**
- 创建：`aeris/models/trace.py`

- [ ] **步骤 1：创建 aeris/models/trace.py**

```python
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field


class LLMTrace(SQLModel, table=True):
    __tablename__ = "llm_traces"

    trace_id: str = Field(primary_key=True, max_length=100)
    user_id: int = Field(foreign_key="users.id", index=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    message_id: Optional[int] = Field(foreign_key="messages.id", default=None)

    # Provider and model info
    provider: str = Field(max_length=50)
    model: str = Field(max_length=100)

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Request/Response payloads
    request_payload: dict = Field(sa_column=Column(JSON))
    response_payload: dict = Field(sa_column=Column(JSON))

    # Performance metrics
    latency_ms: int
    first_token_ms: Optional[int] = Field(default=None)
    tokens_per_second: Optional[float] = Field(default=None)

    # Token usage
    input_tokens: int
    output_tokens: int
    tokens_estimated: bool = Field(default=False)

    # Tool calls
    tool_calls: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    tool_results: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))
    iteration_count: int = Field(default=1)

    # Errors
    error_type: Optional[str] = Field(default=None, max_length=50)
    error_message: Optional[str] = Field(default=None)
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/models/trace.py
git commit -m "feat: add llm_trace model"
```

---

### 任务 9：安全工具模块

**文件：**
- 创建：`aeris/utils/__init__.py`
- 创建：`aeris/utils/security.py`

- [ ] **步骤 1：创建 aeris/utils/__init__.py**

```python
"""Utility modules."""
```

- [ ] **步骤 2：创建 aeris/utils/security.py**

```python
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from aeris.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/utils/__init__.py aeris/utils/security.py
git commit -m "feat: add security utilities (JWT, bcrypt)"
```

---

### 任务 10：认证服务

**文件：**
- 创建：`aeris/services/__init__.py`
- 创建：`aeris/services/auth_service.py`

- [ ] **步骤 1：创建 aeris/services/__init__.py**

```python
"""Business logic services."""
```

- [ ] **步骤 2：创建 aeris/services/auth_service.py**

```python
from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from aeris.models.user import User
from aeris.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, username: str, password: str) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(password)
        user = User(username=username, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    def create_access_token_for_user(self, user: User) -> str:
        """Create access token for user."""
        access_token_expires = timedelta(minutes=30)
        return create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=access_token_expires,
        )
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/services/__init__.py aeris/services/auth_service.py
git commit -m "feat: add auth service with user CRUD"
```

---

### 任务 11：认证路由

**文件：**
- 创建：`aeris/routers/__init__.py`
- 创建：`aeris/routers/auth.py`

- [ ] **步骤 1：创建 aeris/routers/__init__.py**

```python
"""API routers."""
```

- [ ] **步骤 2：创建 aeris/routers/auth.py**

```python
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from aeris.database import get_session
from aeris.services.auth_service import AuthService
from aeris.utils.security import verify_token

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int
    username: str


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    username: str = payload.get("username")
    if user_id is None or username is None:
        raise credentials_exception
    return TokenData(user_id=int(user_id), username=username)


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Register a new user."""
    service = AuthService(session)

    # Check if user exists
    existing_user = await service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    user = await service.create_user(user_data.username, user_data.password)
    return UserResponse(id=user.id, username=user.username, is_active=user.is_active)


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Login and get access token."""
    service = AuthService(session)
    user = await service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = service.create_access_token_for_user(user)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: Annotated[TokenData, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Get current user info."""
    service = AuthService(session)
    user = await service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=user.id, username=user.username, is_active=user.is_active)
```

- [ ] **步骤 3：Commit**

```bash
git add aeris/routers/__init__.py aeris/routers/auth.py
git commit -m "feat: add auth router with register/login/me endpoints"
```

---

### 任务 12：健康检查路由

**文件：**
- 创建：`aeris/routers/health.py`

- [ ] **步骤 1：创建 aeris/routers/health.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from aeris.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "aeris"}


@router.get("/health/db")
async def db_health_check(session: AsyncSession = Depends(get_session)):
    """Database health check endpoint."""
    try:
        result = await session.execute(text("SELECT 1"))
        await result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/routers/health.py
git commit -m "feat: add health check endpoints"
```

---

### 任务 13：主应用入口

**文件：**
- 创建：`aeris/main.py`

- [ ] **步骤 1：创建 aeris/main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aeris.config import get_settings
from aeris.database import init_db
from aeris.routers import auth, health

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="A lightweight AI Agent platform",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to Aeris", "version": settings.version}
```

- [ ] **步骤 2：Commit**

```bash
git add aeris/main.py
git commit -m "feat: add FastAPI main application with router registration"
```

---

### 任务 14：Alembic 数据库迁移配置

**文件：**
- 创建：`alembic.ini`
- 创建：`alembic/env.py`
- 创建：`alembic/script.py.mako`
- 创建：`alembic/versions/.gitkeep`

- [ ] **步骤 1：创建 alembic.ini**

```ini
# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = alembic

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python>=3.9 or backports.zoneinfo library.
# Any required deps can installed by `pip install alembic[tz]`
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os  # Use os.pathsep. Default: "os"

# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
# recursive_version_locations = false

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts. See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the exec runner, execute a binary
# hooks = ruff
# ruff.type = exec
# ruff.executable = %(here)s/.venv/bin/ruff
# ruff.options = --fix REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **步骤 2：创建 alembic/env.py**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from aeris.config import get_settings
from aeris.models import SQLModel

settings = get_settings()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set async database URL
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    async_database_url = database_url

config.set_main_option("sqlalchemy.url", async_database_url)

# add your model's MetaData object here
# for 'autogenerate' support
from aeris.models import User, Conversation, Message, ScheduledTask, FileRecord, LLMTrace

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **步骤 3：创建 alembic/script.py.mako**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **步骤 4：创建 alembic/versions/.gitkeep**

```bash
# empty file to keep directory in git
```

- [ ] **步骤 5：Commit**

```bash
git add alembic.ini alembic/
git commit -m "chore: add alembic configuration for database migrations"
```

---

### 任务 15：测试配置和认证测试

**文件：**
- 创建：`tests/__init__.py`
- 创建：`tests/conftest.py`
- 创建：`tests/test_auth.py`

- [ ] **步骤 1：创建 tests/__init__.py**

```python
"""Test suite."""
```

- [ ] **步骤 2：创建 tests/conftest.py**

```python
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from aeris.main import app
from aeris.database import get_session

# Test database URL (using SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client with overridden database session."""
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
```

- [ ] **步骤 3：创建 tests/test_auth.py**

```python
import pytest


@pytest.mark.asyncio
async def test_register_user(client):
    """Test user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    """Test registration with duplicate username."""
    # First registration
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200

    # Duplicate registration
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "differentpass"},
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client):
    """Test successful login."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )

    # Wrong password
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "wrongpass"},
    )
    assert response.status_code == 401

    # Non-existent user
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent", "password": "testpass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client):
    """Test getting current user info."""
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "testpass123"},
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"},
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aeris"
```

- [ ] **步骤 4：Commit**

```bash
git add tests/
git commit -m "test: add auth tests with async fixtures"
```

---

## 自检

### 规格覆盖度检查

| 规格需求 | 实现任务 |
|---------|---------|
| 单体 FastAPI 应用 | ✅ 任务 13 |
| PostgreSQL 持久化 | ✅ 任务 1, 2, 4 |
| SQLModel ORM | ✅ 任务 5-9 |
| Pydantic Settings | ✅ 任务 3 |
| JWT 认证 | ✅ 任务 9, 10, 11 |
| Docker Compose | ✅ 任务 2 |
| 数据库迁移 | ✅ 任务 14 |
| 测试覆盖 | ✅ 任务 15 |

### 文件职责清晰

- `config.py`：单一职责，配置管理
- `database.py`：单一职责，数据库连接和 session 管理
- `models/*.py`：每个模型独立文件，职责清晰
- `services/auth_service.py`：认证业务逻辑
- `routers/*.py`：HTTP 路由处理
- `utils/security.py`：安全工具函数

### 类型一致性

- 所有模型使用 SQLModel 定义
- 所有 Pydantic schemas 定义明确
- 所有依赖注入使用 `Annotated` 语法

---

## 执行方式

**计划已完成并保存到 `docs/superpowers/plans/2026-04-28-aeris-phase1.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
