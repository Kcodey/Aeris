import uvicorn

from meditatio.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "meditatio.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )