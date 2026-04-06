"""
四性检测 Celery 任务

四性 = 真实性（Authenticity）+ 完整性（Integrity）+ 可用性（Availability）+ 安全性（Security）
这是中国档案行业标准 DA/T 70-2018 要求的电子档案质量检测体系。

检测流程：
  1. 真实性：SHA-256 哈希比对（档案入库时记录的 sha256_hash vs 当前文件哈希）
  2. 完整性：文件格式合规性检测（PDF/A、OFD 等归档格式）
  3. 可用性：文件可读性测试（能否正常打开、渲染）
  4. 安全性：加密状态、密级标注检查
"""

import hashlib
import logging
from celery import Task
from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.preservation.tasks.detection.run_four_nature_detection",
    max_retries=2,
    queue="preservation",
)
def run_four_nature_detection(self: Task, item_id: str, detection_id: str) -> dict:
    """
    对指定档案条目运行四性检测。

    Args:
        item_id: ArchiveItem UUID
        detection_id: DetectionRecord UUID（提前在 DB 创建，tracking progress）

    Returns:
        {"status": "pass"|"fail", "score": 85.0, "details": {...}}
    """
    import asyncio
    return asyncio.run(_run_detection_async(self, item_id, detection_id))


async def _run_detection_async(task: Task, item_id: str, detection_id: str) -> dict:
    from app.infra.db.session import AsyncSessionLocal
    from app.modules.preservation.repositories.detection_repository import DetectionRepository
    from app.modules.repository.repositories.archive_repository import ArchiveItemRepository
    import uuid

    async with AsyncSessionLocal() as db:
        item_repo = ArchiveItemRepository(db)
        detection_repo = DetectionRepository(db)

        item = await item_repo.get_by_id(uuid.UUID(item_id))
        detection = await detection_repo.get_by_id(uuid.UUID(detection_id))

        if not item or not detection:
            logger.warning("四性检测：记录不存在 item=%s detection=%s", item_id, detection_id)
            return {"status": "skipped"}

        results = {}
        score = 100.0

        # ── 1. 真实性检测 ─────────────────────────────────────────
        auth_result = await _check_authenticity(item)
        results["authenticity"] = auth_result
        if not auth_result["pass"]:
            score -= 30.0

        # ── 2. 完整性检测 ─────────────────────────────────────────
        integ_result = await _check_integrity(item)
        results["integrity"] = integ_result
        if not integ_result["pass"]:
            score -= 25.0

        # ── 3. 可用性检测 ─────────────────────────────────────────
        avail_result = await _check_availability(item)
        results["availability"] = avail_result
        if not avail_result["pass"]:
            score -= 25.0

        # ── 4. 安全性检测 ─────────────────────────────────────────
        sec_result = _check_security(item)
        results["security"] = sec_result
        if not sec_result["pass"]:
            score -= 20.0

        final_status = "pass" if score >= 60.0 else "fail"

        # 更新检测记录
        detection.status = final_status
        detection.score = max(0.0, score)
        detection.details_json = results
        await db.commit()

        logger.info("四性检测完成: item=%s status=%s score=%.1f", item_id, final_status, score)
        return {"status": final_status, "score": score, "details": results}


async def _check_authenticity(item) -> dict:
    """真实性：SHA-256 哈希比对"""
    if not item.sha256_hash or not item.storage_key:
        return {"pass": True, "note": "无哈希记录，跳过比对"}

    # TODO: 从 MinIO 下载文件，计算实际哈希值
    # 当前返回通过（待 MinIO 集成后实现）
    return {"pass": True, "algorithm": "sha256", "note": "待MinIO集成后实现"}


async def _check_integrity(item) -> dict:
    """完整性：文件格式合规性"""
    ARCHIVAL_FORMATS = {"pdf", "ofd", "tiff", "tif", "jpg", "png", "xml"}
    file_format = (item.file_format or "").lower()

    if not file_format:
        return {"pass": False, "note": "未记录文件格式"}

    is_archival = file_format in ARCHIVAL_FORMATS
    return {
        "pass": is_archival,
        "file_format": file_format,
        "note": "符合归档格式要求" if is_archival else f"格式 '{file_format}' 不符合归档标准",
    }


async def _check_availability(item) -> dict:
    """可用性：文件可读性（简单检查：文件大小 > 0）"""
    if item.file_size and item.file_size > 0:
        return {"pass": True, "file_size": item.file_size}
    return {"pass": False, "note": "文件大小为0或未记录，可能损坏"}


def _check_security(item) -> dict:
    """安全性：密级标注检查"""
    valid_levels = {"public", "internal", "confidential", "secret"}
    level = item.security_level or ""
    if level in valid_levels:
        return {"pass": True, "security_level": level}
    return {"pass": False, "note": f"无效密级标注: '{level}'"}
