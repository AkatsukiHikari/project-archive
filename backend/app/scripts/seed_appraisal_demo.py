"""开放鉴定 demo：往正式库（repo_archive）造一批"到期待鉴定"档案。

- 年度 1990-2003（满 25 年，进入开放鉴定范围），少量 2022-2024（未到期对照）
- 保管期限混合：永久 / 30年 / 10年
- 密级大部分公开，少量内部/秘密（AI 应判控制使用）
- 题名混入敏感词样本（病历、信访、国防工程、商业秘密……AI 应命中）

复用暂存库里已有的 全宗/目录/门类 组合，不新建基础数据。
幂等：以 DH 前缀 JDDEMO 为标记，已存在即跳过。
运行：cd backend && PYTHONPATH=. uv run python app/scripts/seed_appraisal_demo.py
"""

import asyncio
import random
import sys

sys.path.insert(0, ".")

from sqlalchemy import func, select

import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.infra.db.session import AsyncSessionLocal
from app.modules.repository.models.archive import Archive, ArchiveStaging
from app.modules.repository.models.category import \
    ArchiveCategory  # noqa: F401
from app.modules.repository.models.fonds import Fonds  # noqa: F401

DH_PREFIX = "JDDEMO"

# (题名, 密级)；含敏感词的题名用于验证 AI 预鉴定命中
PLAIN_TITLES = [
    "年度工作总结报告",
    "机关党委会议纪要",
    "财务决算报表",
    "人事任免通知",
    "基建项目竣工验收单",
    "固定资产盘点清册",
    "职工代表大会决议",
    "年度统计年报",
    "公文收发登记簿",
    "档案移交清册",
    "设备采购合同存档",
    "培训工作方案",
]
SENSITIVE_TITLES = [
    ("职工病历档案汇编", "公开"),
    ("信访案件处理记录", "公开"),
    ("国防工程验收报告", "公开"),
    ("商业秘密保护协议存档", "公开"),
    ("离婚调解书存档", "公开"),
    ("外交谈判会谈纪要", "公开"),
    ("涉密项目立项审批表", "内部"),
    ("武器装备保管登记册", "秘密"),
]
BGQX_POOL = ["永久", "永久", "30年", "30年", "10年"]


async def seed() -> None:
    random.seed(42)
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(func.count())
                .select_from(Archive)
                .where(Archive.DH.like(f"{DH_PREFIX}%"))
            )
        ).scalar_one()
        if existing:
            print(f"SKIP：正式库已有 {existing} 条 {DH_PREFIX} 演示档案")
            return

        combos = (
            await db.execute(
                select(
                    ArchiveStaging.fonds_id,
                    ArchiveStaging.catalog_id,
                    ArchiveStaging.category_id,
                    ArchiveStaging.QZH,
                    ArchiveStaging.tenant_id,
                )
                .where(ArchiveStaging.is_deleted.is_(False))
                .distinct()
            )
        ).all()
        if not combos:
            print("暂存库为空，找不到可复用的全宗/目录/门类组合，先跑基础 seed")
            return

        made = 0
        seq = 0
        for fonds_id, catalog_id, category_id, qzh, tenant_id in combos[:3]:
            # 到期档案：1990-2003
            for i in range(20):
                seq += 1
                nd = random.choice(range(1990, 2004))
                if i < len(SENSITIVE_TITLES) and made < len(SENSITIVE_TITLES):
                    tm, mj = SENSITIVE_TITLES[made % len(SENSITIVE_TITLES)]
                else:
                    tm, mj = random.choice(PLAIN_TITLES), "公开"
                db.add(
                    Archive(
                        fonds_id=fonds_id,
                        catalog_id=catalog_id,
                        category_id=category_id,
                        QZH=qzh,
                        DH=f"{DH_PREFIX}-{qzh}-{nd}-{seq:04d}",
                        TM=f"{tm}（{nd}年）",
                        RZZ="档案室",
                        ND=nd,
                        WJRQ=f"{nd}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                        YS=random.randint(2, 60),
                        MJ=mj,
                        BGQX=random.choice(BGQX_POOL),
                        status="archived",
                        tenant_id=tenant_id,
                    )
                )
                made += 1
            # 未到期对照：2022-2024
            for _ in range(4):
                seq += 1
                nd = random.choice([2022, 2023, 2024])
                db.add(
                    Archive(
                        fonds_id=fonds_id,
                        catalog_id=catalog_id,
                        category_id=category_id,
                        QZH=qzh,
                        DH=f"{DH_PREFIX}-{qzh}-{nd}-{seq:04d}",
                        TM=f"{random.choice(PLAIN_TITLES)}（{nd}年）",
                        RZZ="档案室",
                        ND=nd,
                        WJRQ=f"{nd}-06-15",
                        YS=random.randint(2, 30),
                        MJ="公开",
                        BGQX=random.choice(BGQX_POOL),
                        status="archived",
                        tenant_id=tenant_id,
                    )
                )
                made += 1

        await db.commit()
        print(
            f"完成：正式库新增 {made} 条演示档案（其中含敏感词样本 {len(SENSITIVE_TITLES)} 类）"
        )


if __name__ == "__main__":
    asyncio.run(seed())
