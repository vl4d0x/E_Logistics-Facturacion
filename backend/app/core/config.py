"""Application settings, read from environment variables.

Fails fast at startup if a required variable is missing — see `01-architecture §7`.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core / DB ---
    database_url: str = Field(alias="DATABASE_URL")
    env: str = Field(default="development", alias="ENV")

    # --- Auth / JWT ---
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_access_minutes: int = Field(default=30, alias="JWT_ACCESS_MINUTES")
    jwt_refresh_days: int = Field(default=30, alias="JWT_REFRESH_DAYS")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # --- Facturama (PAC) ---
    facturama_env: str = Field(default="sandbox", alias="FACTURAMA_ENV")
    facturama_user: str | None = Field(default=None, alias="FACTURAMA_USER")
    facturama_password: str | None = Field(default=None, alias="FACTURAMA_PASSWORD")

    # --- Cloudflare R2 ---
    r2_endpoint: str | None = Field(default=None, alias="R2_ENDPOINT")
    r2_access_key_id: str | None = Field(default=None, alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(default=None, alias="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field(default="elogistics", alias="R2_BUCKET")

    # --- Resend (correo) ---
    resend_api_key: str | None = Field(default=None, alias="RESEND_API_KEY")
    email_from: str = Field(default="Elogistics <facturacion@dominio.mx>", alias="EMAIL_FROM")

    # --- CORS ---
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    # --- Emisor (persona física) — constantes fiscales, NO hardcodear en código ---
    # 🔴 INFO REQUERIDA (Vlad): confirmar antes de timbrar en real (04-facturacion-cfdi §1).
    emisor_rfc: str | None = Field(default=None, alias="EMISOR_RFC")
    emisor_nombre: str | None = Field(default=None, alias="EMISOR_NOMBRE")
    emisor_regimen_fiscal: str = Field(default="612", alias="EMISOR_REGIMEN_FISCAL")
    emisor_lugar_expedicion: str | None = Field(default=None, alias="EMISOR_LUGAR_EXPEDICION")

    # --- Seed admin (Fase 0, H0.2) ---
    # 🔴 INFO REQUERIDA (Vlad): valores reales del/los admin inicial(es).
    seed_admin_nombre: str = Field(default="Admin", alias="SEED_ADMIN_NOMBRE")
    seed_admin_email: str | None = Field(default=None, alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str | None = Field(default=None, alias="SEED_ADMIN_PASSWORD")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
