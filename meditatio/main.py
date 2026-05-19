from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meditatio.config import get_settings
from meditatio.database import init_db
from meditatio.routers import auth, health, chat, ws, files, tasks, monitoring, timing_admin, skill_usage, rag

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Initialize timing collector
    from meditatio.utils.timing_collector import init_collector, get_collector
    init_collector({
        "ENABLE_TIMING_TRACE": settings.enable_timing_trace,
        "TIMING_FULL_MODE": settings.timing_full_mode,
        "TIMING_QUEUE_SIZE": settings.timing_queue_size,
        "TIMING_SLOW_THRESHOLD_MS": settings.timing_slow_threshold_ms,
    })
    get_collector().start_collecting()

    # Initialize task scheduler
    from meditatio.services.agent_engine import get_agent_engine
    from meditatio.services.task_scheduler import get_task_scheduler

    scheduler = get_task_scheduler()
    scheduler.initialize(get_agent_engine())
    scheduler.start()

    # Initialize skill registry
    from pathlib import Path
    from meditatio.skills.registry import init_skill_registry

    init_skill_registry(Path(settings.skills_dir))

    # Register tools - currently disabled for redesign
    from meditatio.tools.base import get_tool_registry
    # from meditatio.tools.conversation_search import register_conversation_search_tool
    # from meditatio.tools.file_tools import register_file_tools
    # from meditatio.tools.schedule_tools import register_schedule_tools
    # from meditatio.tools.analyze_excel import register_inspect_excel_tool
    from meditatio.tools.bash_tool import register_bash_tool
    from meditatio.tools.load_skill import register_load_skill_tool
    from meditatio.tools.rag_tool import register_rag_tool

    registry = get_tool_registry()
    # register_conversation_search_tool(registry)
    # register_file_tools(registry)
    # register_schedule_tools(registry)
    # register_inspect_excel_tool(registry)
    register_bash_tool(registry)
    register_load_skill_tool(registry)
    register_rag_tool(registry)

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
app.include_router(monitoring.router, prefix="/api/v1")
app.include_router(skill_usage.router, prefix="/api/v1")
app.include_router(timing_admin.router)  # Timing admin routes (no prefix for admin)
app.include_router(ws.router)
app.include_router(rag.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Aeris", "version": settings.version}
