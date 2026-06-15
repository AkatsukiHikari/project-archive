"""档案收集 demo：归档计划 + 移交单（各状态）+ 移交明细 + 批量导入任务。

让 归档移交 / 接收登记 / 收集台账 / 批量导入 四个页面都有真实数据：
  - 归档计划：5 个单位 × 2025 年度应交计划（收集台账"催交看板"依据）
  - 移交单：覆盖 草稿/待接收/已签收/已接收入库/已退回 全部状态
  - 移交明细：每单 6~12 条 DA/T 字段条目
  - 批量导入任务：3 条 done 历史（含成功/失败统计）

幂等：以移交单号前缀 YJDEMO 为标记，已存在即跳过。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_collection_demo.py
"""

import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")

from sqlalchemy import func, select

import app.modules.iam.models.tenant  # noqa: F401
from app.infra.db.session import AsyncSessionLocal
from app.modules.collection.models.import_task import ImportTask
from app.modules.collection.models.transfer import TransferBatch, TransferEntry
from app.modules.collection.models.transfer_plan import TransferPlan
from app.modules.iam.models.user import User
from app.modules.repository.models.archive import Catalog
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.fonds import Fonds

MARK = "YJDEMO"

UNITS = [
    "党政办公室",
    "财务结算中心",
    "人力资源部",
    "基建管理处",
    "纪检监察室",
]
TITLES = [
    "年度工作计划",
    "党组会议纪要",
    "财务收支凭证",
    "干部考核表",
    "项目招标文件",
    "设备验收报告",
    "信访接待登记",
    "公文处理单",
    "合同协议正本",
    "统计报表汇编",
    "请示与批复",
    "会议签到簿",
]
MJ_POOL = ["无", "无", "无", "秘密", "机密"]
BGQX_POOL = ["permanent", "long", "long", "short"]

# 状态 → (生成数, 是否预检过)
STATUS_PLAN = [
    ("draft", 2),
    ("submitted", 3),
    ("received", 2),
    ("accepted", 2),
    ("returned", 1),
]


def _entries(batch_id, tenant_id, n: int) -> list[TransferEntry]:
    rows = []
    for i in range(n):
        nd = random.choice([2023, 2024, 2025])
        rows.append(
            TransferEntry(
                batch_id=batch_id,
                row_no=i + 1,
                TM=f"{random.choice(TITLES)}（{nd}）",
                RZZ=random.choice(UNITS),
                ND=nd,
                WJRQ=f"{nd}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                YS=random.randint(2, 50),
                MJ=random.choice(MJ_POOL),
                BGQX=random.choice(BGQX_POOL),
                precheck_status=random.choice(["pending", "ok", "ok", "warning"]),
                tenant_id=tenant_id,
            )
        )
    return rows


async def seed() -> None:
    random.seed(20260613)
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(func.count())
                .select_from(TransferBatch)
                .where(TransferBatch.transfer_no.like(f"{MARK}%"))
            )
        ).scalar_one()
        if existing:
            print(f"SKIP：已有 {existing} 条 {MARK} 演示移交单")
            return

        fonds_list = (
            (
                await db.execute(
                    select(Fonds)
                    .where(Fonds.is_deleted.is_(False))
                    .order_by(Fonds.fonds_code)
                )
            )
            .scalars()
            .all()
        )
        category = (
            (
                await db.execute(
                    select(ArchiveCategory)
                    .where(ArchiveCategory.is_deleted.is_(False))
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        catalog = (
            (
                await db.execute(
                    select(Catalog).where(Catalog.is_deleted.is_(False)).limit(1)
                )
            )
            .scalars()
            .first()
        )
        admin = (
            (await db.execute(select(User).where(User.username == "admin")))
            .scalars()
            .first()
        )
        if not fonds_list or not category or not catalog:
            print("缺少全宗 / 门类 / 目录基础数据，请先跑基础 seed")
            return
        tenant_id = fonds_list[0].tenant_id

        # ── 归档计划（催交看板）──
        plan_n = 0
        for i, unit in enumerate(UNITS):
            fonds = fonds_list[i % len(fonds_list)]
            db.add(
                TransferPlan(
                    year=2025,
                    source_unit=unit,
                    fonds_id=fonds.id,
                    category_id=category.id,
                    planned_count=random.randint(20, 80),
                    due_date=date(2025, 12, 31),
                    status="active",
                    notes="2025 年度归档移交计划",
                    tenant_id=tenant_id,
                )
            )
            plan_n += 1

        # ── 移交单（各状态）──
        now = datetime.now(timezone.utc)
        seq = 0
        batch_n = entry_n = 0
        for status, count in STATUS_PLAN:
            for _ in range(count):
                seq += 1
                unit = UNITS[seq % len(UNITS)]
                fonds = fonds_list[seq % len(fonds_list)]
                n_entries = random.randint(6, 12)
                created = now - timedelta(days=random.randint(1, 60))

                batch = TransferBatch(
                    transfer_no=f"{MARK}{date.today():%Y%m%d}{seq:03d}",
                    source_unit=unit,
                    fonds_id=fonds.id,
                    category_id=category.id,
                    year=random.choice([2024, 2025]),
                    handover_person=random.choice(["张明", "李静", "王磊", "赵敏"]),
                    handover_date=created.date(),
                    expected_count=n_entries,
                    status=status,
                    notes=f"{unit} 移交",
                    tenant_id=tenant_id,
                )
                # 状态相关时间线 + 预检
                if status in ("submitted", "received", "accepted", "returned"):
                    batch.submitted_at = created + timedelta(hours=2)
                if status in ("received", "accepted"):
                    batch.received_at = created + timedelta(days=1)
                    batch.handler_id = admin.id if admin else None
                    batch.precheck_score = round(random.uniform(82, 99), 1)
                    batch.precheck_passed = True
                    batch.catalog_id = None
                if status == "accepted":
                    batch.accepted_at = created + timedelta(days=2)
                if status == "returned":
                    batch.received_at = created + timedelta(days=1)
                    batch.precheck_score = round(random.uniform(40, 58), 1)
                    batch.precheck_passed = False
                    batch.return_reason = (
                        "四性预检未通过：部分条目缺少责任者/文件日期，退回补充"
                    )

                db.add(batch)
                await db.flush()
                for e in _entries(batch.id, tenant_id, n_entries):
                    db.add(e)
                    entry_n += 1
                batch_n += 1

        # ── 批量导入历史 ──
        import_n = 0
        for i in range(3):
            total = random.randint(50, 200)
            failed = random.randint(0, 8)
            created = now - timedelta(days=random.randint(3, 40))
            db.add(
                ImportTask(
                    category_id=category.id,
                    fonds_id=fonds_list[0].id,
                    catalog_id=catalog.id,
                    operator_id=admin.id if admin else None,
                    status="done",
                    original_filename=f"{MARK}_档案著录_{i + 1}.xlsx",
                    total=total,
                    success=total - failed,
                    failed=failed,
                    skipped=0,
                    started_at=created,
                    finished_at=created + timedelta(minutes=2),
                    tenant_id=tenant_id,
                )
            )
            import_n += 1

        await db.commit()
        print(
            f"完成：归档计划 {plan_n} 个，移交单 {batch_n} 张（{entry_n} 条明细），导入历史 {import_n} 条"
        )


if __name__ == "__main__":
    asyncio.run(seed())
