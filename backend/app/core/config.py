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

    # MINIO / MinIO 私有对象存储
    MINIO_ENDPOINT: str = "localhost:9000"      # host:port（不含协议）
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False                  # True = HTTPS
    # 浏览器可直接访问的 MinIO 公网 URL（与 MINIO_ENDPOINT 一致或 CDN 域名）
    MINIO_PUBLIC_URL: str = "http://localhost:9000"

    # ALIYUN OSS
    OSS_ACCESS_KEY_ID: str | None = None
    OSS_ACCESS_KEY_SECRET: str | None = None
    OSS_ENDPOINT: str | None = None

    # SECURITY — 必填，无默认值，生产环境必须通过 .env 注入
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",   # admin-web dev
        "http://localhost:3001",   # public-portal dev
    ]

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

    # ── Elasticsearch ──
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # ── RabbitMQ / Celery ──
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"

    # ── 初始化数据 ──
    ADMIN_EMAIL: str = "admin@sams.local"
    ADMIN_PASSWORD: str = ""
    SKIP_SEED: bool = False

    # ── AI / RAG ──
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen2.5:7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    DIFY_BASE_URL: str = "http://localhost/v1"
    DIFY_API_KEY: str = ""

    # 旧方案（9 个独立 chatbot；保留作为兜底，不删）
    DIFY_API_KEY_QA: str = ""
    DIFY_API_KEY_SEARCH: str = ""
    DIFY_API_KEY_SUMMARY: str = ""
    DIFY_API_KEY_ATTACH: str = ""
    DIFY_API_KEY_CATALOG: str = ""
    DIFY_API_KEY_FOURNAT: str = ""
    DIFY_API_KEY_DRAFT: str = ""
    DIFY_API_KEY_RELATE: str = ""
    DIFY_API_KEY_KB_MANAGE: str = ""
    DIFY_API_KEY_APPRAISAL: str = ""
    DIFY_API_KEY_RESEARCH: str = ""

    # A' 方案：1 主 Chatflow + 8 子 Workflow
    DIFY_MASTER_API_KEY: str = ""
    DIFY_WF_API_KEY_QA: str = ""
    DIFY_WF_API_KEY_SEARCH: str = ""
    DIFY_WF_API_KEY_SUMMARY: str = ""
    DIFY_WF_API_KEY_ATTACH: str = ""
    DIFY_WF_API_KEY_CATALOG: str = ""
    DIFY_WF_API_KEY_FOURNAT: str = ""
    DIFY_WF_API_KEY_DRAFT: str = ""
    DIFY_WF_API_KEY_RELATE: str = ""
    DIFY_WF_API_KEY_KB_MANAGE: str = ""

    def dify_api_key_for(self, scenario_code: str) -> str:
        """按场景拿 API Key；优先用旧 chatbot 的 key（向后兼容）。"""
        attr = f"DIFY_API_KEY_{scenario_code.upper()}"
        return getattr(self, attr, "") or self.DIFY_API_KEY

    def dify_wf_api_key_for(self, scenario_code: str) -> str:
        """A' 方案：按 scenario_code 拿子 Workflow 的 API Key。"""
        attr = f"DIFY_WF_API_KEY_{scenario_code.upper()}"
        return getattr(self, attr, "")

    # ── AI Agent 系统（P1 引入；见 docs/superpowers/specs/2026-05-11-archive-ai-agent-design.md） ──
    # 启用的能力码列表，逗号分隔；9 个场景全部开启
    AI_ENABLED_CAPABILITIES: str = "qa,search,summary,attach,catalog,fournat,draft,relate,kb_manage"
    # 默认模型档位：快 / 准 / 思考
    AI_DEFAULT_MODEL_TIER: str = "准"
    # Tool 回调 token 有效期（秒），用于 Dify → 后端工具调用时恢复用户身份。
    # 注意：Dify chatflow 会在「会话创建时」冻结 inputs，后续轮次复用首轮的 user_token，
    # 因此 TTL 必须覆盖整段会话寿命，否则多轮对话超过 TTL 后 dispatch 会 401。
    # 该 token 仅在 后端↔Dify↔后端 闭环内流转、不下发浏览器；真正的调用方鉴权由
    # AI_SERVICE_TOKEN（X-Service-Token）承担，故此处放宽到 24h 是安全的。
    AI_USER_TOKEN_TTL_SECONDS: int = 86400
    # Patch 默认闸门：auto / review / manual
    AI_PATCH_DEFAULT_GATE: str = "review"
    # 是否强制引用（无 evidence 拒答）
    AI_CITATION_REQUIRED: bool = True
    # 评测回归是否阻断 Workflow 升级（true=回退到上一版本）
    AI_EVAL_BLOCK_ON_REGRESSION: bool = True
    # AI Tool 服务令牌（Dify 回调后端的双向认证用）
    AI_SERVICE_TOKEN: str = ""

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
