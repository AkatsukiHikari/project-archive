from typing import Dict, Any, List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SAMS"
    API_PREFIX: str = "/api"

    # DATABASE
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "sams"
    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> str:
        if isinstance(v, str):
            return v
        return f"postgresql+asyncpg://{info.data.get('POSTGRES_USER')}:{info.data.get('POSTGRES_PASSWORD')}@{info.data.get('POSTGRES_SERVER')}/{info.data.get('POSTGRES_DB')}"

    # REDIS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # STORAGE
    STORAGE_TYPE: str = "local"  # local, aws, minio, alioss
    STORAGE_LOCAL_ROOT: str = "./storage_data"

    # AWS S3
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str = "sams-archive"

    # MINIO / STORAGE / S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "sams-archive"
    MINIO_SECURE: bool = False

    # ALIYUN OSS
    OSS_ACCESS_KEY_ID: str | None = None
    OSS_ACCESS_KEY_SECRET: str | None = None
    OSS_ENDPOINT: str | None = None

    # SECURITY
    SECRET_KEY: str = "sams_secret_key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # ── OAuth2 SSO ──
    OAUTH_CLIENTS: Dict[str, Any] = {
        "admin-web": {
            "redirect_uris": ["http://localhost:3000/auth/callback"],
            "name": "管理后台",
        },
        "public-portal": {
            "redirect_uris": ["http://localhost:3001/auth/callback"],
            "name": "公众查档门户",
        },
    }
    SESSION_EXPIRE_HOURS: int = 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
