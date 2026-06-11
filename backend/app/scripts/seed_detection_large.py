"""给一组档案挂"大文件"原文，并实测一次真实批次检测耗时。

目的：用真实大小（~20MB/件）的原文，验证四性检测的耗时来自 I/O 而非哈希。
- 选取同一 (全宗, 目录) 下的若干档案，软删旧附件，各挂一个 ~20MB 的 PDF
- 直接调用 PreservationService.run_batch 跑一次，打印真实耗时
- 同时对相同字节量做纯 SHA256 微基准，做对比

运行：uv run python -m app.scripts.seed_detection_large
"""
import asyncio
import hashlib
import io
import os
import time

from sqlalchemy import func, select, update

from app.infra.db.session import AsyncSessionLocal
import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.modules.iam.models.user import User
from app.infra.storage.factory import storage
from app.modules.repository.models.archive import ArchiveAttachment, ArchiveStaging
from app.modules.preservation.services.scheme_service import PreservationService
from app.scripts.seed_detection_demo import build_pdf

FILE_MB = 20      # 每个原文大小
MAX_FILES = 8     # 挂几件


def build_large_pdf(title: str, size_bytes: int) -> bytes:
    """合法 PDF 头 + 不可压缩随机负载，凑到目标大小（模拟扫描件体量）。"""
    base = build_pdf(title)
    pad = size_bytes - len(base)
    # 追加在 %%EOF 之后：头检测仍识别为 PDF，i11 对全字节算哈希
    return base + b"\n%% bulk-payload\n" + os.urandom(max(pad, 0))


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # 选一个 archive 最多的 (全宗, 目录) 组
        grp = (await db.execute(
            select(ArchiveStaging.fonds_id, ArchiveStaging.catalog_id, func.count().label("n"))
            .where(ArchiveStaging.is_deleted == False, ArchiveStaging.fonds_id.isnot(None))  # noqa: E712
            .group_by(ArchiveStaging.fonds_id, ArchiveStaging.catalog_id)
            .order_by(func.count().desc()).limit(1)
        )).first()
        if not grp:
            print("没有可用的档案分组"); return
        fonds_id, catalog_id, n = grp
        rows = (await db.execute(
            select(ArchiveStaging).where(
                ArchiveStaging.is_deleted == False,  # noqa: E712
                ArchiveStaging.fonds_id == fonds_id,
                ArchiveStaging.catalog_id == catalog_id,
            ).limit(MAX_FILES)
        )).scalars().all()

        size = FILE_MB * 1024 * 1024
        total_bytes = 0
        for a in rows:
            # 软删旧附件，避免一档多附件干扰
            await db.execute(update(ArchiveAttachment)
                             .where(ArchiveAttachment.archive_id == a.id)
                             .values(is_deleted=True))
            pdf = build_large_pdf(a.TM or "archive", size)
            total_bytes += len(pdf)
            key = f"archive/{a.id}/yuanwen_large.pdf"
            storage.save(io.BytesIO(pdf), key, "archives", "application/pdf")
            db.add(ArchiveAttachment(
                archive_id=a.id, is_staging=True, is_primary=True,
                original_name=f"{a.DH or a.TM}.pdf"[:200], storage_key=key, storage_bucket="archives",
                file_size=len(pdf), file_format="pdf", page_count=2,
                sha256_hash=hashlib.sha256(pdf).hexdigest(), tenant_id=a.tenant_id,
            ))
        await db.commit()
        print(f"已挂大文件 {len(rows)} 件 × {FILE_MB}MB（全宗={fonds_id} 目录={catalog_id}），共 {total_bytes/1024/1024:.0f} MB")

        # —— 纯哈希微基准：相同字节量本地 SHA256 要多久 ——
        blob = os.urandom(size)
        t = time.perf_counter()
        for _ in range(len(rows)):
            hashlib.sha256(blob).hexdigest()
        hash_ms = (time.perf_counter() - t) * 1000

        # —— 真实批次检测：含 MinIO 下载 + 重算哈希 + 字段校验 ——
        operator = (await db.execute(select(User).limit(1))).scalars().first()
        svc = PreservationService(db)
        t = time.perf_counter()
        batch = await svc.run_batch(
            scheme_id=None, fonds_id=fonds_id, catalog_id=catalog_id,
            category_id=None, nd=None,
            operator_id=operator.id if operator else None,
            tenant_id=rows[0].tenant_id,
        )
        await db.commit()
        run_ms = (time.perf_counter() - t) * 1000

        print("\n================  实测  ================")
        print(f"文件: {batch.total} 件 × {FILE_MB}MB = {total_bytes/1024/1024:.0f}MB")
        print(f"纯 SHA256（仅哈希这些字节）: {hash_ms:.1f} ms")
        print(f"完整批次检测（下载+哈希+字段校验+落库）: {run_ms:.1f} ms")
        print(f"→ 哈希只占 {hash_ms/run_ms*100:.1f}%，其余 {run_ms-hash_ms:.0f}ms 全是 I/O（MinIO 下载 + DB）")
        print(f"批次 {batch.batch_no}: 合格 {batch.passed} / 不合格 {batch.failed} / 待复核 {batch.pending}，均分 {batch.avg_score}")


if __name__ == "__main__":
    asyncio.run(seed())
