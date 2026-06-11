"""四性检测 demo：给暂存档案批量挂真实 PDF 原文，让检测有文件可下载/校验。

大部分为合规件(检测可判合格)；按比例造少量"不合格"对照：
  - 篡改件：固化值与真实哈希不符 → 校验值检测 fail
  - 坏格式：声明 docx → 格式合规 fail

幂等：已有附件的档案跳过。
运行：uv run python -m app.scripts.seed_detection_demo
"""
import asyncio
import hashlib
import io
import uuid

from sqlalchemy import select

from app.infra.db.session import AsyncSessionLocal
import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.infra.storage.factory import storage
from app.modules.repository.models.archive import ArchiveAttachment, ArchiveStaging


def build_pdf(title: str) -> bytes:
    def pc(t):
        s = ("BT /F1 14 Tf 60 740 Td (" + t + ") Tj ET").encode("latin-1", "replace")
        return b"<< /Length " + str(len(s)).encode() + b" >>\nstream\n" + s + b"\nendstream"
    pages = [f"SAMS archive original - {title[:40]}", "page 2 - electronic record body"]
    n = len(pages)
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(n))
    b = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
         2: ("<< /Type /Pages /Kids [" + kids + "] /Count " + str(n) + " >>").encode()}
    fo = 3 + n * 2
    for i, t in enumerate(pages):
        p, c = 3 + i * 2, 4 + i * 2
        b[p] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents " + str(c) + " 0 R /Resources << /Font << /F1 " + str(fo) + " 0 R >> >> >>").encode()
        b[c] = pc(t)
    b[fo] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    out = io.BytesIO(); out.write(b"%PDF-1.4\n"); off = {}
    for i in range(1, fo + 1):
        off[i] = out.tell(); out.write(f"{i} 0 obj\n".encode() + b[i] + b"\nendobj\n")
    xp = out.tell(); N = fo + 1
    out.write(f"xref\n0 {N}\n".encode()); out.write(b"0000000000 65535 f \n")
    for i in range(1, N):
        out.write(f"{off[i]:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {N} /Root 1 0 R >>\nstartxref\n{xp}\n%%EOF".encode())
    return out.getvalue()


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        archives = (await db.execute(
            select(ArchiveStaging).where(ArchiveStaging.is_deleted == False)  # noqa: E712
        )).scalars().all()
        has_att = set((await db.execute(select(ArchiveAttachment.archive_id))).scalars().all())

        made = tampered = badfmt = 0
        for idx, a in enumerate(archives):
            if a.id in has_att:
                continue
            pdf = build_pdf(a.TM or "archive")
            key = f"archive/{a.id}/yuanwen.pdf"
            storage.save(io.BytesIO(pdf), key, "archives", "application/pdf")
            real = hashlib.sha256(pdf).hexdigest()

            sha = real
            fmt = "pdf"
            if idx % 11 == 5:        # ~1/11 篡改
                sha = hashlib.sha256(b"tampered").hexdigest(); tampered += 1
            elif idx % 13 == 7:      # ~1/13 坏格式
                fmt = "docx"; badfmt += 1

            db.add(ArchiveAttachment(
                archive_id=a.id, is_staging=True, is_primary=True,
                original_name=f"{a.DH or a.TM}.pdf"[:200], storage_key=key, storage_bucket="archives",
                file_size=len(pdf), file_format=fmt, page_count=2, sha256_hash=sha,
                tenant_id=a.tenant_id,
            ))
            made += 1
        await db.commit()
        print(f"已挂原文 {made} 件（含 篡改对照 {tampered} 件、坏格式对照 {badfmt} 件）")


if __name__ == "__main__":
    asyncio.run(seed())
