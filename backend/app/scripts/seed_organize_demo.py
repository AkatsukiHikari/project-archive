"""档案整理 demo：待整理暂存档案 + 按档号命名的数字化成果样例文件。

造的数据覆盖整理页全部演示场景：
  - 12 条有档号的暂存档案，并在 backend/testdata/digitized/ 生成同名 PDF
    →  演示「批量挂接数字化成果」（文件名 = 档号）
  -  5 条没有档号的暂存档案
    →  演示「按档号规则批量重编档号」（同时创建演示用档号规则）
  -  3 条有档号但不生成 PDF
    →  挂接预检里出现"档案无文件"的对照
  -  另生成 2 个对不上任何档号的 PDF + 1 个假 OFD
    →  挂接预检里出现"无此档号"的对照
  - 全部档案可勾选演示「批量修改」与「归档入库」

幂等：以 DH/TM 前缀 ZLDEMO 为标记，已存在即跳过。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_organize_demo.py
"""

import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, ".")

from sqlalchemy import func, select

import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.infra.db.session import AsyncSessionLocal
from app.modules.repository.models.archive import ArchiveStaging
from app.modules.repository.models.category import \
    ArchiveCategory  # noqa: F401
from app.modules.repository.models.fonds import Fonds  # noqa: F401
from app.modules.repository.models.no_rule import ArchiveNoRule

MARK = "ZLDEMO"
OUT_DIR = Path("testdata/digitized")

WITH_DH_TITLES = [
    "行政办公会议纪要",
    "年度财务预算报告",
    "干部任免审批表",
    "基建项目立项批复",
    "设备采购验收单",
    "对外合作框架协议",
    "年度档案工作总结",
    "规章制度汇编",
    "安全生产检查记录",
    "信息系统建设方案",
    "职工培训计划",
    "公务接待登记表",
]
NO_DH_TITLES = [
    "收文登记簿",
    "发文稿纸存根",
    "工作联系函",
    "请示报告底稿",
    "会议签到册",
]
NO_FILE_TITLES = ["实物档案移交清单", "声像档案著录卡", "荣誉证书登记表"]


def build_pdf(title: str) -> bytes:
    """极简单页 PDF（不引第三方库）。"""

    def pc(t: str) -> bytes:
        s = ("BT /F1 14 Tf 60 740 Td (" + t + ") Tj ET").encode("latin-1", "replace")
        return (
            b"<< /Length "
            + str(len(s)).encode()
            + b" >>\nstream\n"
            + s
            + b"\nendstream"
        )

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        4: pc(f"SAMS digitized copy - {title[:40]}"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = {}
    for i in range(1, 6):
        offsets[i] = out.tell()
        out.write(f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 6\n0000000000 65535 f \n")
    for i in range(1, 6):
        out.write(f"{offsets[i]:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return out.getvalue()


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(func.count())
                .select_from(ArchiveStaging)
                .where(
                    ArchiveStaging.DH.like(f"{MARK}%"),
                    ArchiveStaging.is_deleted.is_(False),
                )
            )
        ).scalar_one()
        if existing:
            print(f"SKIP：暂存库已有 {existing} 条 {MARK} 演示档案")
            return

        combo = (
            await db.execute(
                select(
                    ArchiveStaging.fonds_id,
                    ArchiveStaging.catalog_id,
                    ArchiveStaging.category_id,
                    ArchiveStaging.QZH,
                    ArchiveStaging.tenant_id,
                )
                .where(ArchiveStaging.is_deleted.is_(False))
                .limit(1)
            )
        ).first()
        if not combo:
            print("暂存库为空，找不到可复用的全宗/目录/门类，先跑基础 seed")
            return
        fonds_id, catalog_id, category_id, qzh, tenant_id = combo

        # 演示用档号规则：QZH-WS-年度-序号（4位，目录+年度内连续）
        rule_exists = (
            await db.execute(
                select(ArchiveNoRule.id).where(
                    ArchiveNoRule.name == "文书档号规则(演示)",
                    ArchiveNoRule.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if not rule_exists:
            db.add(
                ArchiveNoRule(
                    category_id=category_id,
                    name="文书档号规则(演示)",
                    rule_template={
                        "separator": "-",
                        "segments": [
                            {"type": "field", "field": "QZH"},
                            {"type": "literal", "value": "WS"},
                            {"type": "field", "field": "ND"},
                            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
                        ],
                    },
                    seq_scope="catalog_year",
                    is_active=True,
                    tenant_id=tenant_id,
                )
            )
            print("  INSERT 档号规则 文书档号规则(演示) QZH-WS-ND-NNNN")

        def staging(tm: str, nd: int, dh: str | None, seq: int) -> ArchiveStaging:
            return ArchiveStaging(
                fonds_id=fonds_id,
                catalog_id=catalog_id,
                category_id=category_id,
                QZH=qzh,
                DH=dh,
                TM=f"{MARK} {tm}",
                RZZ="办公室",
                ND=nd,
                WJRQ=f"{nd}-{(seq % 12) + 1:02d}-{(seq % 27) + 1:02d}",
                YS=seq % 30 + 2,
                MJ="public",
                BGQX="short",
                status="pending_review",
                tenant_id=tenant_id,
            )

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        seq = 0

        # ① 有档号 + 生成同名 PDF（批量挂接主角）
        for tm in WITH_DH_TITLES:
            seq += 1
            dh = f"{MARK}-{qzh}-2025-{seq:04d}"
            db.add(staging(tm, 2025, dh, seq))
            (OUT_DIR / f"{dh}.pdf").write_bytes(build_pdf(tm))

        # ② 无档号（重编档号主角）
        for tm in NO_DH_TITLES:
            seq += 1
            db.add(staging(tm, 2025, None, seq))

        # ③ 有档号但无文件（挂接对照）
        for tm in NO_FILE_TITLES:
            seq += 1
            db.add(staging(tm, 2025, f"{MARK}-{qzh}-2025-{seq:04d}", seq))

        # ④ 对不上档号的文件（挂接对照）
        (OUT_DIR / "UNKNOWN-0001.pdf").write_bytes(build_pdf("无主文件一"))
        (OUT_DIR / "UNKNOWN-0002.pdf").write_bytes(build_pdf("无主文件二"))
        (OUT_DIR / f"{MARK}-{qzh}-2025-0001.ofd").write_bytes(b"OFD-DEMO-PAYLOAD")

        await db.commit()
        total = len(WITH_DH_TITLES) + len(NO_DH_TITLES) + len(NO_FILE_TITLES)
        print(
            f"完成：暂存库新增 {total} 条待整理档案；"
            f"数字化成果样例已生成到 {OUT_DIR.resolve()}（PDF {len(WITH_DH_TITLES) + 2} 个 + OFD 1 个）"
        )


if __name__ == "__main__":
    asyncio.run(seed())
