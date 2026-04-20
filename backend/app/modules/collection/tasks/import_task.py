"""
批量导入异步 Celery 任务。

流程：
  1. 读取 ImportTask，拉取文件
  2. 按 mapping_snapshot 转换每行数据
  3. 每 500 条为一批：写 PG → bulk ES → 推 WebSocket 进度
  4. 生成失败报表（XLSX），上传对象存储
  5. 更新 ImportTask.status = done / failed
"""
import asyncio
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from celery import Task

from celery_app import celery_app

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


@celery_app.task(
    bind=True,
    name="app.modules.collection.tasks.import_task.execute_import",
    max_retries=0,          # 导入任务不自动重试，失败原因记录在报表里
    queue="default",
)
def execute_import(self: Task, task_id: str) -> dict:
    return asyncio.run(_execute_import_async(task_id))


async def _execute_import_async(task_id_str: str) -> dict:
    from app.infra.db.session import AsyncSessionLocal
    from app.infra.storage.factory import storage
    from app.modules.collection.models.import_task import ImportTask
    from app.modules.collection.repositories.import_repo import ImportTaskRepository
    from app.modules.collection.services.file_parser import parse_file
    from app.modules.collection.services.import_service import (
        _apply_mapping, _validate_row, build_archive_from_row,
    )
    from app.modules.repository.models.fonds import Fonds
    from app.modules.repository.services.es_sync_service import bulk_sync
    from app.modules.repository.services.no_rule_engine import ArchiveNoEngine
    from app.modules.repository.services.no_rule_service import NoRuleService
    from sqlalchemy import select

    task_id = uuid.UUID(task_id_str)
    _IMPORT_BUCKET = "import-staging"

    async with AsyncSessionLocal() as db:
        repo = ImportTaskRepository(db)
        task = await repo.get_by_id(task_id)
        if not task:
            logger.error("ImportTask %s 不存在", task_id_str)
            return {"status": "error", "reason": "task not found"}

        # 标记运行中
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # 读文件
            file_bytes = storage.get(task.file_key, _IMPORT_BUCKET)
            _, rows = parse_file(file_bytes, task.original_filename or "file.csv")

            mapping: dict = {
                m["source_col"]: m["target_field"]
                for m in (task.mapping_snapshot or [])
            }

            # 获取全宗号（用于构建 Archive.fonds_code）
            fonds_result = await db.execute(
                select(Fonds).where(Fonds.id == task.fonds_id)
            )
            fonds = fonds_result.scalar_one_or_none()
            fonds_code = fonds.fonds_code if fonds else ""

            # 获取激活的档号规则（如有）
            no_rule_engine = ArchiveNoEngine(db)
            from app.modules.repository.models.category import ArchiveCategory
            cat_result = await db.execute(
                select(ArchiveCategory).where(ArchiveCategory.id == task.category_id)
            )
            category = cat_result.scalar_one_or_none()
            active_rule = None
            if category and category.archive_no_rule_id:
                svc = NoRuleService(db)
                try:
                    active_rule = await svc.get(category.archive_no_rule_id)
                except Exception:
                    pass  # 没有规则时跳过

            success_count = 0
            failed_count = 0
            failed_rows: list[dict] = []

            # 分批处理
            batch: list = []
            for i, row in enumerate(rows, start=2):
                mapped = _apply_mapping(row, mapping)
                issues = _validate_row(mapped)
                if any(s == "error" for s, _ in issues):
                    failed_count += 1
                    failed_rows.append({"row": i, "reason": "; ".join(m for _, m in issues), **row})
                    continue

                archive = build_archive_from_row(
                    mapped, task.fonds_id, task.catalog_id,
                    task.category_id, fonds_code, task.tenant_id,
                )

                # 生成档号
                if active_rule:
                    try:
                        archive.archive_no = await no_rule_engine.generate(active_rule, archive)
                    except Exception as exc:
                        logger.warning("档号生成失败 row=%d: %s", i, exc)

                batch.append(archive)

                if len(batch) >= BATCH_SIZE:
                    s, f, fr = await _flush_batch(db, batch, failed_rows)
                    success_count += s
                    failed_count += f
                    failed_rows.extend(fr)
                    # 推 WebSocket 进度
                    await _push_progress(task_id_str, i, success_count, failed_count, len(rows))
                    batch = []

            # 剩余不满一批
            if batch:
                s, f, fr = await _flush_batch(db, batch, [])
                success_count += s
                failed_count += f
                failed_rows.extend(fr)

            # 生成失败报表
            report_key: Optional[str] = None
            if failed_rows:
                report_key = await _generate_report(failed_rows, task_id_str, storage)

            task.success = success_count
            task.failed = failed_count
            task.total = len(rows)
            task.status = "done"
            task.error_report_key = report_key
            task.finished_at = datetime.now(timezone.utc)
            await db.commit()

            return {"status": "done", "success": success_count, "failed": failed_count}

        except Exception as exc:
            logger.error("导入任务 %s 异常终止: %s", task_id_str, exc, exc_info=True)
            task.status = "failed"
            task.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return {"status": "failed", "error": str(exc)}


async def _flush_batch(db, archives: list, _existing_failed: list) -> tuple[int, int, list]:
    """将一批 Archive 写入 PG，然后 bulk index 到 ES。"""
    from app.modules.repository.services.es_sync_service import bulk_sync

    success = 0
    failed = 0
    failed_rows: list[dict] = []

    for archive in archives:
        db.add(archive)

    try:
        await db.flush()
        success = len(archives)
        # 批量同步 ES（失败不阻断）
        await bulk_sync(archives)
    except Exception as exc:
        logger.warning("批量写入 PG 失败，逐条重试: %s", exc)
        await db.rollback()
        # 逐条重试，记录失败原因
        for archive in archives:
            try:
                db.add(archive)
                await db.flush()
                success += 1
            except Exception as row_exc:
                failed += 1
                failed_rows.append({"title": archive.title, "reason": str(row_exc)})
                await db.rollback()

    return success, failed, failed_rows


async def _push_progress(
    task_id: str, current_row: int, success: int, failed: int, total: int
) -> None:
    """通过 Redis pub/sub 推送进度，WebSocket 路由订阅后转发给前端。"""
    try:
        from app.infra.cache.redis import get_redis
        redis = await get_redis()
        import json
        payload = json.dumps({
            "task_id": task_id,
            "current": current_row,
            "success": success,
            "failed": failed,
            "total": total,
        })
        await redis.publish(f"import_progress:{task_id}", payload)
    except Exception:
        pass  # 进度推送失败不阻断导入


async def _generate_report(failed_rows: list[dict], task_id: str, storage) -> Optional[str]:
    """生成失败明细 XLSX 报表，上传对象存储，返回文件键。"""
    import xlsxwriter
    try:
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet("失败明细")

        if not failed_rows:
            wb.close()
            return None

        headers = list(failed_rows[0].keys())
        for col, h in enumerate(headers):
            ws.write(0, col, h)
        for row_idx, row in enumerate(failed_rows, start=1):
            for col, h in enumerate(headers):
                ws.write(row_idx, col, str(row.get(h, "")))
        wb.close()

        buf.seek(0)
        key = f"import-reports/{task_id}_errors.xlsx"
        storage.save(buf, key, "import-staging", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        return key
    except Exception as exc:
        logger.warning("生成失败报表异常: %s", exc)
        return None
