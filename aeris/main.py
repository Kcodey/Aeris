from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aeris.config import get_settings
from aeris.database import init_db
from aeris.routers import auth, health, chat, ws, files

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()

    # Register tools
    from aeris.tools.base import get_tool_registry
    from aeris.tools.conversation_search import register_conversation_search_tool

    registry = get_tool_registry()
    register_conversation_search_tool(registry)

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
app.include_router(chat.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(ws.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Aeris", "version": settings.version}
