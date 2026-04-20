"""
Celery 应用入口

启动 Worker：
  cd backend
  celery -A celery_app worker --loglevel=info -Q default,embedding,preservation

队列说明：
  default       — 通用任务
  embedding     — 档案向量化任务（耗时，与业务隔离）
  preservation  — 四性检测任务（CPU密集，独立Worker可单独扩容）

学习笔记：
  Celery 是 Python 最流行的异步任务队列。
  架构：Producer（FastAPI发布任务）→ Broker（RabbitMQ传递消息）→ Worker（执行任务）→ Backend（Redis存结果）
  为什么需要异步任务？档案向量化、四性检测可能需要几分钟，不能让用户的 HTTP 请求等那么久。
  用 Celery 把任务交给后台 Worker，HTTP 请求立即返回"任务已提交"，用户不感知等待。
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "sams",
    broker=settings.RABBITMQ_URL,
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/2",  # Redis DB 2 存任务结果
    include=[
        "app.modules.repository.tasks.embedding",
        "app.modules.repository.tasks.es_rebuild",
        "app.modules.collection.tasks.import_task",
        "app.modules.preservation.tasks.detection",
    ],
)

celery_app.conf.update(
    # 序列化格式
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务结果过期时间
    result_expires=3600 * 24,  # 24小时
    # 任务路由（不同类型任务进不同队列）
    task_routes={
        "app.modules.repository.tasks.embedding.*": {"queue": "embedding"},
        "app.modules.repository.tasks.es_rebuild.*": {"queue": "default"},
        "app.modules.collection.tasks.import_task.*": {"queue": "default"},
        "app.modules.preservation.tasks.detection.*": {"queue": "preservation"},
    },
    # Worker 并发数（CPU 密集型任务建议等于 CPU 核数）
    worker_concurrency=4,
    # 单个 Worker 每次预取任务数（避免大任务独占）
    worker_prefetch_multiplier=1,
)
