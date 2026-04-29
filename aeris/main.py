from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aeris.config import get_settings
from aeris.database import init_db
from aeris.routers import auth, health, chat, ws, files, tasks

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Initialize task scheduler
    from aeris.services.agent_engine import get_agent_engine
    from aeris.services.task_scheduler import get_task_scheduler

    scheduler = get_task_scheduler()
    scheduler.initialize(get_agent_engine())
    scheduler.start()

    # Register tools
    from aeris.tools.base import get_tool_registry
    from aeris.tools.conversation_search import register_conversation_search_tool
    from aeris.tools.file_tools import register_file_tools
    from aeris.tools.schedule_tools import register_schedule_tools

    registry = get_tool_registry()
    register_conversation_search_tool(registry)
    register_file_tools(registry)
    register_schedule_tools(registry)

    yield

    # Shutdown
    scheduler.shutdown()


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
app.include_router(chat.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(ws.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Aeris", "version": settings.version}
