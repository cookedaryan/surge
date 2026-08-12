from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "SURGE GIS Optimization Service"
    version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    api_v2_prefix: str = "/api/v2"

    environment: Literal[
        "development",
        "testing",
        "production",
    ] = "development"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
