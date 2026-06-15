"""档案保管 demo：库房（含架位网格）+ 出入库记录。

  - 4 个库房，不同填充率 / 温湿度 / 网格规模（库房管理三维展示 + 卡片）
  - 架位网格按 rows×columns 自动生成，随机占用率（三维着色）
  - 出入库记录：借阅出库（在外/已归还）、修复出库、数字化出库、移库等

幂等：以库房编号前缀 KF 为标记，已存在即跳过。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_storage_demo.py
"""

import asyncio
import random
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")

from sqlalchemy import func, select

import app.modules.iam.models.tenant  # noqa: F401
from app.infra.db.session import AsyncSessionLocal
from app.modules.iam.models.user import User
from app.modules.repository.models.archive import Archive
from app.modules.storage.models import StorageInout, StorageShelf, StorageVault

VAULTS = [
    {
        "code": "KF-A",
        "name": "一号档案库（综合）",
        "location": "档案楼 2 层东区",
        "area": 320.0,
        "rows": 5,
        "columns": 8,
        "layers": 6,
        "capacity": 12000,
        "fill": 0.72,
        "temp": 19.8,
        "hum": 51.0,
    },
    {
        "code": "KF-B",
        "name": "二号档案库（文书）",
        "location": "档案楼 2 层西区",
        "area": 280.0,
        "rows": 4,
        "columns": 6,
        "layers": 5,
        "capacity": 8000,
        "fill": 0.45,
        "temp": 20.3,
        "hum": 48.5,
    },
    {
        "code": "KF-C",
        "name": "三号档案库（声像实物）",
        "location": "档案楼 3 层",
        "area": 200.0,
        "rows": 3,
        "columns": 5,
        "layers": 4,
        "capacity": 4000,
        "fill": 0.91,
        "temp": 18.5,
        "hum": 45.0,
    },
    {
        "code": "KF-D",
        "name": "四号档案库（待整理）",
        "location": "档案楼 1 层",
        "area": 150.0,
        "rows": 3,
        "columns": 4,
        "layers": 4,
        "capacity": 3000,
        "fill": 0.20,
        "temp": 21.0,
        "hum": 55.0,
    },
]


async def seed() -> None:
    random.seed(613)
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(func.count())
                .select_from(StorageVault)
                .where(StorageVault.code.like("KF-%"))
            )
        ).scalar_one()
        if existing:
            print(f"SKIP：已有 {existing} 个库房")
            return

        admin = (
            (await db.execute(select(User).where(User.username == "admin")))
            .scalars()
            .first()
        )
        tenant_id = admin.tenant_id if admin else None

        for v in VAULTS:
            used = int(v["capacity"] * v["fill"])
            vault = StorageVault(
                code=v["code"],
                name=v["name"],
                location=v["location"],
                area_sqm=v["area"],
                rows=v["rows"],
                columns=v["columns"],
                layers=v["layers"],
                capacity=v["capacity"],
                used=used,
                temperature=v["temp"],
                humidity=v["hum"],
                status="maintenance" if v["code"] == "KF-D" else "active",
                manager_id=admin.id if admin else None,
                tenant_id=tenant_id,
            )
            db.add(vault)
            await db.flush()

            # 架位网格 + 随机占用（围绕库房整体填充率波动）
            per = max(1, v["capacity"] // (v["rows"] * v["columns"]))
            for r in range(v["rows"]):
                for c in range(v["columns"]):
                    ratio = min(1.0, max(0.0, random.gauss(v["fill"], 0.18)))
                    db.add(
                        StorageShelf(
                            vault_id=vault.id,
                            code=f"{chr(65 + r)}-{c + 1:02d}",
                            row_index=r,
                            col_index=c,
                            capacity=per,
                            used=int(per * ratio),
                            tenant_id=tenant_id,
                        )
                    )

        await db.flush()

        # 出入库记录：取几件正式库档案做样例
        archives = (
            (
                await db.execute(
                    select(Archive).where(Archive.is_deleted.is_(False)).limit(12)
                )
            )
            .scalars()
            .all()
        )
        vault_a = (
            (await db.execute(select(StorageVault).where(StorageVault.code == "KF-A")))
            .scalars()
            .first()
        )

        now = datetime.now(timezone.utc)
        biz_samples = [
            ("borrow", "out", "李研究员", "借阅出库"),
            ("borrow", "returned", "王主任", "借阅出库（已归还）"),
            ("repair", "out", "古籍修复室", "破损修复出库"),
            ("digitize", "out", "数字化加工中心", "数字化扫描出库"),
            ("relocate", "in", "库房管理员", "整理后回库"),
            ("inventory", "in", "年度盘点小组", "盘点入库核对"),
        ]
        n = 0
        for i, a in enumerate(archives):
            biz, status, party, note = biz_samples[i % len(biz_samples)]
            created = now - timedelta(days=random.randint(1, 45))
            direction = (
                "in"
                if status in ("done", "returned") and biz in ("relocate", "inventory")
                else ("out" if status in ("out", "returned") else "in")
            )
            rec = StorageInout(
                record_no=f"{'CK' if direction == 'out' else 'RK'}{date.today():%Y%m%d}{i + 1:03d}",
                direction=direction,
                biz_type=biz,
                archive_id=a.id,
                DH=a.DH,
                TM=a.TM,
                qty=1,
                vault_id=vault_a.id if vault_a else None,
                counterparty=party,
                status=status,
                notes=note,
                operator_id=admin.id if admin else None,
                tenant_id=tenant_id,
            )
            if direction == "out":
                rec.out_time = created
                rec.expected_return = created + timedelta(days=30)
                if status == "returned":
                    rec.in_time = created + timedelta(days=random.randint(3, 20))
            else:
                rec.in_time = created
                rec.status = "done"
            db.add(rec)
            n += 1

        await db.commit()
        print(f"完成：库房 {len(VAULTS)} 个（含架位网格），出入库记录 {n} 条")


if __name__ == "__main__":
    asyncio.run(seed())
