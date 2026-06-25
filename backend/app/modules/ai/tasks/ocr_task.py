"""OCR Celery 任务（可选）。

当前默认执行路径是 API 进程内 asyncio 后台任务（见 ocr_job_service.enqueue），
因为本部署 API 原生跑、worker 容器到不了 localhost 的 Dify。
此 Celery 包装保留：未来整体容器化、worker 能访问 Dify 时可切换为队列执行。
"""

import asyncio

from celery import Task

from celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.modules.ai.tasks.ocr_task.run_ocr_job",
    max_retries=0,
    queue="default",
)
def run_ocr_job(self: Task, job_id: str) -> dict:
    from app.modules.ai.services.ocr_job_service import run_job

    return asyncio.run(run_job(job_id))
