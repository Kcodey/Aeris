import uvicorn

from aeris.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "aeris.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )