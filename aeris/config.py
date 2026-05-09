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
    skills_dir: str = "./skills"

    # LLM Provider Configuration
    provider_type: str = "sglang"  # "sglang" or "volcano"

    # SGLang Provider
    sglang_base_url: str = "http://localhost:30000/v1"
    sglang_model: str = "default"

    # Volcano Provider (火山引擎)
    volcano_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    volcano_api_key: str = ""
    volcano_model: str = ""

    # Performance Timing Trace
    enable_timing_trace: bool = False
    timing_full_mode: bool = False
    timing_queue_size: int = 10000
    timing_slow_threshold_ms: int = 3000


@lru_cache
def get_settings() -> Settings:
    return Settings()
