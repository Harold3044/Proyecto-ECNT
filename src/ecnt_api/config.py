"""Configuración de la API (variables de entorno con prefijo ECNT_ o archivo .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from ecnt_core.config import ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ECNT_", env_file=ROOT / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(ROOT / 'data' / 'storage' / 'ecnt.db').as_posix()}"
    storage_dir: Path = ROOT / "data" / "storage"
    jwt_secret: str = "solo-desarrollo-cambie-este-secreto-en-el-archivo-env-0123456789"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120
    cors_origins: str = "http://localhost:8501,http://localhost:8502"
    bootstrap_admin_email: str = "admin@ecnt.local"
    bootstrap_admin_password: str = "Admin2026!"
    bootstrap_eps_email: str = "eps@ecnt.local"
    bootstrap_eps_password: str = "Eps2026!"
    bootstrap_investigador_email: str = "investigador@ecnt.local"
    bootstrap_investigador_password: str = "Inv2026!"
    min_cell_size: int = 10  # supresión de conteos pequeños en el ambiente EPS
    max_upload_mb: int = 25

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
