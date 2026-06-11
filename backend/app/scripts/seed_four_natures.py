"""四性检测：种子检测项目录 + 默认"电子文件基础四性检测方案"。

幂等：已存在的检测项按 code 跳过；已有默认方案则不重复建。
运行：uv run python -m app.scripts.seed_four_natures
"""
import asyncio

from sqlalchemy import select

from app.infra.db.session import AsyncSessionLocal
import app.modules.iam.models.tenant  # noqa: F401
import app.modules.iam.models.user  # noqa: F401
from app.modules.preservation.models.scheme import CheckItem, DetectionScheme, SchemeItem
from app.modules.preservation.services.checks.builtin import CATALOG

_DIM_ORDER = {"authenticity": 0, "integrity": 1, "usability": 2, "safety": 3}


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = {c for c in (await db.execute(select(CheckItem.code))).scalars().all()}
        added = 0
        for it in CATALOG:
            if it["code"] in existing:
                continue
            db.add(CheckItem(
                code=it["code"], name=it["name"], dimension=it["dimension"], exec_type=it["exec_type"],
                standard_ref=it.get("standard_ref"), description=it.get("description"),
                carrier_type=it.get("carrier_type", "electronic"),
                default_params=it.get("default_params"), default_weight=it.get("default_weight", 10),
                default_blocking=it.get("default_blocking", False), builtin=True, enabled=True,
            ))
            added += 1
        await db.flush()
        print(f"检测项目录：新增 {added}，共 {len(CATALOG)} 项")

        has_default = (await db.execute(
            select(DetectionScheme).where(DetectionScheme.is_default == True, DetectionScheme.is_deleted == False)  # noqa: E712
        )).scalar_one_or_none()
        if has_default:
            print("默认方案已存在，跳过")
            await db.commit()
            return

        ordered = sorted(CATALOG, key=lambda x: (_DIM_ORDER.get(x["dimension"], 9), x["code"]))

        def add_scheme(name, desc, items, is_default):
            s = DetectionScheme(name=name, description=desc, carrier_type="electronic",
                                is_default=is_default, version=1, status="active")
            db.add(s)
            return s

        async def add_items(scheme, items):
            await db.flush()
            for i, it in enumerate(items):
                db.add(SchemeItem(
                    scheme_id=scheme.id, check_code=it["code"], enabled=True,
                    params=it.get("default_params"), weight=it.get("default_weight", 10),
                    is_blocking=it.get("default_blocking", False), sort_order=i,
                ))

        # 默认 = 自动检测(纯 rule，可全自动判合格/不合格)
        auto = [it for it in ordered if it["exec_type"] == "rule"]
        s1 = add_scheme("电子档案自动四性检测", "DA/T 70-2018 中可机检的指标，全自动判定", auto, True)
        await add_items(s1, auto)
        # 完整 = 全部 45 项(含 AI/人工复核)
        s2 = add_scheme("DA/T 70-2018 四性完整检测(45项)", "全部 45 项国标指标，含 AI 与人工复核", ordered, False)
        await add_items(s2, ordered)

        await db.commit()
        print(f"已建默认方案「{s1.name}」({len(auto)} 项) + 完整方案「{s2.name}」({len(ordered)} 项)")


if __name__ == "__main__":
    asyncio.run(seed())
