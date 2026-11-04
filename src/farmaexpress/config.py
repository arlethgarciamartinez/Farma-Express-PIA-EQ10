"""Configuración 12-Factor: todo viene del entorno (ver .env.example)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./farmaexpress.db"
    app_env: str = "development"
    log_level: str = "INFO"
    auto_create_schema: bool = True
    seed_on_startup: bool = False
    data_dir: str = "datos"
