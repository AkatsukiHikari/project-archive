"""
利用登记 demo 数据：造一批"已办结"的利用申请 + 调阅篮明细，
让利用台账（统计报表：趋势/方式/目的/门类）有数据可看。

幂等：已存在 >= 12 条 completed 申请则跳过。
运行：uv run python -m app.scripts.seed_util_demo
"""
import asyncio
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.infra.db.session import AsyncSessionLocal
import app.modules.iam.models.tenant  # noqa: F401  (确保 FK 目标表已注册)
import app.modules.iam.models.user  # noqa: F401
from app.modules.repository.models.archive import ArchiveStaging
from app.modules.utilization.models.application import (
    UtilizationApplication,
    UtilizationItem,
)

# 与 ArchiveStaging 同租户，保证利用台账（按 tenant 过滤）能查到
TENANT_ID = uuid.UUID("3e9cd294-9d87-4ef0-92b0-75563f5986e3")
HANDLER_ID = uuid.UUID("673e541a-8399-4dd2-a3eb-b7b2cb1b0e2d")  # admin

NAMES = ["张伟", "王芳", "李娜", "刘洋", "陈静", "杨磊", "赵敏", "黄强", "周婷", "吴勇", "徐丽", "孙鹏"]
ORGS = ["市规划局", "市财政局", "市档案馆", "市委办公室", "某律师事务所", "市地方志办", "市第一中学", "个人"]
USE_TYPES = ["read", "read", "read", "borrow", "borrow", "copy", "certificate"]
PURPOSES = ["工作查考", "学术研究", "经济建设", "编史修志", "诉讼维权", "个人事务", "其他"]
GENDERS = ["男", "女"]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        done = (await db.execute(
            select(func.count()).select_from(UtilizationApplication)
            .where(UtilizationApplication.status == "completed")
        )).scalar_one()
        if done >= 12:
            print(f"已有 {done} 条 completed 利用申请，跳过 demo 造数")
            return

        archives = (await db.execute(
            select(ArchiveStaging).where(ArchiveStaging.is_deleted == False).limit(60)  # noqa: E712
        )).scalars().all()
        if not archives:
            print("暂存库无档案，无法造利用明细")
            return

        rng = random.Random(20260609)
        # 跨 8 个月分布（2025-11 .. 2026-06），每月若干条
        months = [(2025, 11), (2025, 12), (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5), (2026, 6)]
        seq = 0
        total_apps = 0
        for (y, m) in months:
            n = rng.randint(2, 5)
            for _ in range(n):
                seq += 1
                day = rng.randint(1, 27)
                ts = datetime(y, m, day, rng.randint(9, 17), rng.randint(0, 59), tzinfo=timezone.utc)
                app = UtilizationApplication(
                    reg_no=f"LY{y}{m:02d}{day:02d}{seq:03d}",
                    applicant_name=rng.choice(NAMES),
                    id_card_no=f"110101{y}{m:02d}{rng.randint(1000, 9999)}",
                    gender=rng.choice(GENDERS),
                    phone=f"139{rng.randint(10000000, 99999999)}",
                    organization=rng.choice(ORGS),
                    purpose=rng.choice(PURPOSES),
                    use_type=rng.choice(USE_TYPES),
                    status="completed",
                    handler_id=HANDLER_ID,
                    tenant_id=TENANT_ID,
                    create_by=HANDLER_ID,
                    create_time=ts,
                    completed_at=ts,
                )
                db.add(app)
                await db.flush()
                for a in rng.sample(archives, rng.randint(1, 4)):
                    db.add(UtilizationItem(
                        application_id=app.id, archive_id=a.id,
                        DH=a.DH, TM=a.TM, RZZ=a.RZZ, ND=a.ND, QZH=a.QZH,
                        tenant_id=TENANT_ID, create_by=HANDLER_ID, create_time=ts,
                    ))
                total_apps += 1
        await db.commit()
        print(f"已造 {total_apps} 条 completed 利用申请（含调阅篮明细），跨 {len(months)} 个月")


if __name__ == "__main__":
    asyncio.run(seed())
