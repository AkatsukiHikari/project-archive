"""初始化系统内置数据字典。

运行方式：
    uv run python app/scripts/seed_sys_dicts.py

幂等：已存在的 dict_type 跳过，不重复插入。
"""
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.modules.iam.models.dict import SysDict, SysDictItem

# ── 内置字典定义 ───────────────────────────────────────────────────────────────

BUILTIN_DICTS: list[dict] = [
    {
        "dict_type": "AI_CATALOG_CONFIG",
        "dict_name": "智能著录配置",
        "description": "智能著录 AI 补正的相似度/置信度阈值（百分比，≥此值自动预勾选）",
        "sort_order": 5,
        "items": [
            {"item_value": "80", "item_label": "相似度/置信度阈值(%)", "is_default": True, "sort_order": 1},
        ],
    },
    {
        "dict_type": "MJ",
        "dict_name": "密级",
        "description": "档案保密等级，依据《保守国家秘密法》",
        "sort_order": 10,
        "items": [
            {"item_value": "公开",   "item_label": "公开",   "is_default": True,  "sort_order": 1},
            {"item_value": "内部",   "item_label": "内部",   "is_default": False, "sort_order": 2},
            {"item_value": "秘密",   "item_label": "秘密",   "is_default": False, "sort_order": 3},
            {"item_value": "机密",   "item_label": "机密",   "is_default": False, "sort_order": 4},
            {"item_value": "绝密",   "item_label": "绝密",   "is_default": False, "sort_order": 5},
        ],
    },
    {
        "dict_type": "BGQX",
        "dict_name": "保管期限",
        "description": "档案保存年限，依据《机关档案管理规定》",
        "sort_order": 20,
        "items": [
            {"item_value": "永久",  "item_label": "永久",  "is_default": False, "sort_order": 1},
            {"item_value": "30年",  "item_label": "30年",  "is_default": True,  "sort_order": 2},
            {"item_value": "10年",  "item_label": "10年",  "is_default": False, "sort_order": 3},
        ],
    },
    {
        "dict_type": "KFZT",
        "dict_name": "开放状态",
        "description": "档案对外开放状态",
        "sort_order": 30,
        "items": [
            {"item_value": "开放",   "item_label": "开放",   "is_default": True,  "sort_order": 1},
            {"item_value": "控制使用", "item_label": "控制使用", "is_default": False, "sort_order": 2},
            {"item_value": "延期开放", "item_label": "延期开放", "is_default": False, "sort_order": 3},
            {"item_value": "不开放",  "item_label": "不开放",  "is_default": False, "sort_order": 4},
        ],
    },
    {
        "dict_type": "DCDJ",
        "dict_name": "档次等级",
        "description": "档案实物载体等级",
        "sort_order": 40,
        "items": [
            {"item_value": "一级", "item_label": "一级", "is_default": False, "sort_order": 1},
            {"item_value": "二级", "item_label": "二级", "is_default": False, "sort_order": 2},
            {"item_value": "三级", "item_label": "三级", "is_default": True,  "sort_order": 3},
        ],
    },
    {
        "dict_type": "DJJG",
        "dict_name": "登记机关",
        "description": "婚姻/不动产等登记机关类型",
        "sort_order": 50,
        "items": [
            {"item_value": "民政局",    "item_label": "民政局",    "is_default": False, "sort_order": 1},
            {"item_value": "自然资源局", "item_label": "自然资源局", "is_default": False, "sort_order": 2},
            {"item_value": "不动产中心", "item_label": "不动产中心", "is_default": False, "sort_order": 3},
            {"item_value": "其他",      "item_label": "其他",      "is_default": False, "sort_order": 4},
        ],
    },
    {
        "dict_type": "ZTXS",
        "dict_name": "载体形式",
        "description": "档案原件的载体类型",
        "sort_order": 60,
        "items": [
            {"item_value": "纸质",   "item_label": "纸质",   "is_default": True,  "sort_order": 1},
            {"item_value": "电子",   "item_label": "电子",   "is_default": False, "sort_order": 2},
            {"item_value": "照片",   "item_label": "照片",   "is_default": False, "sort_order": 3},
            {"item_value": "录音录像", "item_label": "录音录像", "is_default": False, "sort_order": 4},
            {"item_value": "实物",   "item_label": "实物",   "is_default": False, "sort_order": 5},
        ],
    },
    {
        "dict_type": "HYZT",
        "dict_name": "婚姻状态",
        "description": "登记类型",
        "sort_order": 70,
        "items": [
            {"item_value": "结婚",   "item_label": "结婚",   "is_default": True,  "sort_order": 1},
            {"item_value": "离婚",   "item_label": "离婚",   "is_default": False, "sort_order": 2},
            {"item_value": "补领证件", "item_label": "补领证件", "is_default": False, "sort_order": 3},
        ],
    },
    {
        "dict_type": "TXGS",
        "dict_name": "图像格式",
        "description": "照片/图像文件格式",
        "sort_order": 80,
        "items": [
            {"item_value": "JPEG", "item_label": "JPEG", "is_default": True,  "sort_order": 1},
            {"item_value": "PNG",  "item_label": "PNG",  "is_default": False, "sort_order": 2},
            {"item_value": "TIFF", "item_label": "TIFF", "is_default": False, "sort_order": 3},
            {"item_value": "RAW",  "item_label": "RAW",  "is_default": False, "sort_order": 4},
        ],
    },
    {
        "dict_type": "WJRQ_FMT",
        "dict_name": "文件日期格式",
        "description": "文件日期填写格式规范",
        "sort_order": 90,
        "items": [
            {"item_value": "YYYY-MM-DD", "item_label": "YYYY-MM-DD（精确到日）", "is_default": True,  "sort_order": 1},
            {"item_value": "YYYY-MM",    "item_label": "YYYY-MM（精确到月）",    "is_default": False, "sort_order": 2},
            {"item_value": "YYYY",       "item_label": "YYYY（精确到年）",       "is_default": False, "sort_order": 3},
        ],
    },
    {
        "dict_type": "LYFS",
        "dict_name": "利用方式",
        "description": "档案利用方式",
        "sort_order": 100,
        "items": [
            {"item_value": "read",        "item_label": "查阅",     "is_default": True,  "sort_order": 1},
            {"item_value": "borrow",      "item_label": "借阅",     "is_default": False, "sort_order": 2},
            {"item_value": "copy",        "item_label": "复制",     "is_default": False, "sort_order": 3},
            {"item_value": "certificate", "item_label": "出具证明", "is_default": False, "sort_order": 4},
        ],
    },
    {
        "dict_type": "LYMD",
        "dict_name": "利用目的",
        "description": "档案利用目的",
        "sort_order": 110,
        "items": [
            {"item_value": "工作查考", "item_label": "工作查考", "is_default": True,  "sort_order": 1},
            {"item_value": "学术研究", "item_label": "学术研究", "is_default": False, "sort_order": 2},
            {"item_value": "经济建设", "item_label": "经济建设", "is_default": False, "sort_order": 3},
            {"item_value": "编史修志", "item_label": "编史修志", "is_default": False, "sort_order": 4},
            {"item_value": "诉讼维权", "item_label": "诉讼维权", "is_default": False, "sort_order": 5},
            {"item_value": "个人事务", "item_label": "个人事务", "is_default": False, "sort_order": 6},
            {"item_value": "其他",     "item_label": "其他",     "is_default": False, "sort_order": 7},
        ],
    },
]


# ── 执行 ──────────────────────────────────────────────────────────────────────

async def seed() -> None:
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        inserted_dicts = 0
        inserted_items = 0

        for d in BUILTIN_DICTS:
            # 检查是否已存在
            exists = (await session.execute(
                select(SysDict.id).where(
                    SysDict.dict_type == d["dict_type"],
                    SysDict.is_deleted.is_(False),
                )
            )).scalar_one_or_none()

            if exists:
                print(f"  SKIP   {d['dict_type']:12s} {d['dict_name']}")
                continue

            dict_obj = SysDict(
                dict_type=d["dict_type"],
                dict_name=d["dict_name"],
                description=d.get("description"),
                sort_order=d.get("sort_order", 0),
                is_builtin=True,
            )
            session.add(dict_obj)
            await session.flush()

            for item in d.get("items", []):
                session.add(SysDictItem(
                    dict_type=d["dict_type"],
                    item_value=item["item_value"],
                    item_label=item["item_label"],
                    is_default=item.get("is_default", False),
                    sort_order=item.get("sort_order", 0),
                ))
                inserted_items += 1

            print(f"  INSERT {d['dict_type']:12s} {d['dict_name']} ({len(d['items'])} 项)")
            inserted_dicts += 1

        await session.commit()
        print(f"\n完成：新增 {inserted_dicts} 个字典，{inserted_items} 个字典项")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
