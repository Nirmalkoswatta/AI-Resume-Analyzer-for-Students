from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

RUBRIC_VERSION = "2026.09.1"
MODEL_VERSION = "fixture"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESUME_API_", frozen=True)

    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    max_upload_bytes: int = 5 * 1024 * 1024
    max_page_count: int = 10
    min_characters_per_page: int = 120
    log_level: str = "info"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
