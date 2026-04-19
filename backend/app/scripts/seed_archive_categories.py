"""
初始化内置档案门类（DA/T 标准 + 专业档案）。
幂等：已存在的 code 跳过，不重复插入。
运行：cd backend && python -m app.scripts.seed_archive_categories
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings

# Import all models so SQLAlchemy metadata resolves cross-module FKs
import app.modules.iam.models.user  # noqa: F401
import app.modules.iam.models.permission  # noqa: F401
from app.modules.repository.models.category import ArchiveCategory

BUILTIN_CATEGORIES = [
    {"code": "WS", "name": "文书档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "doc_no",   "label": "文号",    "type": "text",   "required": False, "inherited": False},
         {"name": "doc_type", "label": "文件类型", "type": "select", "required": False,
          "options": ["通知", "请示", "报告", "批复", "决定", "会议纪要", "其他"], "inherited": False},
     ]},
    {"code": "KJ", "name": "科技档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "project_code", "label": "项目编号", "type": "text",   "required": False, "inherited": False},
         {"name": "drawing_type", "label": "图纸类别", "type": "select", "required": False,
          "options": ["施工图", "竣工图", "草图", "设计图"], "inherited": False},
         {"name": "version",      "label": "版本号",   "type": "text",   "required": False, "inherited": False},
     ]},
    {"code": "HJ", "name": "会计档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "voucher_type",   "label": "凭证类型", "type": "select", "required": False,
          "options": ["记账凭证", "银行凭证", "报销凭证"], "inherited": False},
         {"name": "account_period", "label": "会计期间", "type": "text",   "required": False, "inherited": False},
     ]},
    {"code": "ZP", "name": "照片档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "photo_subject",  "label": "摄影主题", "type": "text", "required": False, "inherited": False},
         {"name": "photographer",   "label": "摄影者",   "type": "text", "required": False, "inherited": False},
         {"name": "shoot_location", "label": "拍摄地点", "type": "text", "required": False, "inherited": False},
     ]},
    {"code": "SX", "name": "声像档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "media_type",   "label": "媒体类型", "type": "select", "required": False,
          "options": ["音频", "视频"], "inherited": False},
         {"name": "duration_sec", "label": "时长(秒)", "type": "number", "required": False, "inherited": False},
     ]},
    {"code": "DZ", "name": "电子档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": []},
    {"code": "SW", "name": "实物档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": [
         {"name": "material",   "label": "材质", "type": "text",   "required": False, "inherited": False},
         {"name": "dimensions", "label": "尺寸", "type": "text",   "required": False, "inherited": False},
         {"name": "quantity",   "label": "数量", "type": "number", "required": False, "inherited": False},
     ]},
    # 专业档案父类
    {"code": "ZY", "name": "专业档案", "requires_privacy_guard": False, "parent_id_code": None,
     "field_schema": []},
    # 专业档案子类
    {"code": "ZY_HY", "name": "婚姻档案", "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "party_a_name",    "label": "当事人甲姓名",  "type": "text",   "required": True,  "inherited": False},
         {"name": "party_a_id",      "label": "当事人甲证件号", "type": "text",  "required": True,  "inherited": False},
         {"name": "party_b_name",    "label": "当事人乙姓名",  "type": "text",   "required": True,  "inherited": False},
         {"name": "party_b_id",      "label": "当事人乙证件号", "type": "text",  "required": True,  "inherited": False},
         {"name": "marriage_status", "label": "婚姻状态",      "type": "select", "required": True,
          "options": ["结婚", "离婚"], "inherited": False},
         {"name": "reg_authority",   "label": "登记机关",      "type": "text",   "required": False, "inherited": False},
     ]},
    {"code": "ZY_FP", "name": "扶贫档案", "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "household_head", "label": "户主姓名",   "type": "text",   "required": True,  "inherited": False},
         {"name": "head_id",        "label": "户主证件号", "type": "text",   "required": True,  "inherited": False},
         {"name": "poverty_reason", "label": "致贫原因",   "type": "select", "required": False,
          "options": ["因病", "因残", "因学", "因灾", "缺劳力", "缺技术", "其他"], "inherited": False},
         {"name": "exit_time",      "label": "退出时间",   "type": "date",   "required": False, "inherited": False},
     ]},
    {"code": "ZY_TQ", "name": "土地确权档案", "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "owner_name", "label": "权利人姓名", "type": "text",   "required": True,  "inherited": False},
         {"name": "owner_id",   "label": "证件号",     "type": "text",   "required": True,  "inherited": False},
         {"name": "parcel_no",  "label": "地块编号",   "type": "text",   "required": True,  "inherited": False},
         {"name": "area_mu",    "label": "面积(亩)",   "type": "number", "required": False, "inherited": False},
         {"name": "cert_date",  "label": "发证日期",   "type": "date",   "required": False, "inherited": False},
     ]},
    {"code": "ZY_SC", "name": "出生医疗证明", "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "newborn_name", "label": "新生儿姓名", "type": "text", "required": True,  "inherited": False},
         {"name": "birth_date",   "label": "出生日期",   "type": "date", "required": True,  "inherited": False},
         {"name": "mother_name",  "label": "母亲姓名",   "type": "text", "required": True,  "inherited": False},
         {"name": "mother_id",    "label": "母亲证件号", "type": "text", "required": True,  "inherited": False},
         {"name": "hospital",     "label": "接生机构",   "type": "text", "required": False, "inherited": False},
         {"name": "cert_no",      "label": "证件编号",   "type": "text", "required": False, "inherited": False},
     ]},
    {"code": "ZY_TY", "name": "退役军人档案", "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "veteran_name",  "label": "姓名",     "type": "text",   "required": True,  "inherited": False},
         {"name": "veteran_id",    "label": "证件号",   "type": "text",   "required": True,  "inherited": False},
         {"name": "service_years", "label": "服役年限", "type": "number", "required": False, "inherited": False},
         {"name": "troop_no",      "label": "部队番号", "type": "text",   "required": False, "inherited": False},
         {"name": "retire_type",   "label": "退役类型", "type": "select", "required": False,
          "options": ["安置", "自主就业", "退休"], "inherited": False},
     ]},
    {"code": "ZY_DB", "name": "低保档案", "requires_privacy_guard": True, "parent_id_code": "ZY",
     "field_schema": [
         {"name": "household_head", "label": "户主姓名", "type": "text",   "required": True,  "inherited": False},
         {"name": "family_members", "label": "家庭人口", "type": "number", "required": False, "inherited": False},
         {"name": "subsidy_type",   "label": "低保类别", "type": "select", "required": False,
          "options": ["城市低保", "农村低保"], "inherited": False},
         {"name": "approve_org",    "label": "审批机关", "type": "text",   "required": False, "inherited": False},
         {"name": "start_date",     "label": "起始日期", "type": "date",   "required": False, "inherited": False},
     ]},
]


async def seed(db: AsyncSession) -> None:
    code_to_id: dict[str, object] = {}

    # 第一轮：插入顶级门类（parent_id_code=None）
    for item in BUILTIN_CATEGORIES:
        if item["parent_id_code"] is not None:
            continue
        result = await db.execute(
            select(ArchiveCategory).where(ArchiveCategory.code == item["code"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            code_to_id[item["code"]] = existing.id
            print(f"  skip existing: {item['code']}")
            continue
        cat = ArchiveCategory(
            code=item["code"],
            name=item["name"],
            is_builtin=True,
            requires_privacy_guard=item["requires_privacy_guard"],
            field_schema=item["field_schema"] or None,
        )
        db.add(cat)
        await db.flush()
        code_to_id[item["code"]] = cat.id
        print(f"  inserted: {item['code']} {item['name']}")

    # 第二轮：插入子门类（专业档案子类）
    for item in BUILTIN_CATEGORIES:
        if item["parent_id_code"] is None:
            continue
        result = await db.execute(
            select(ArchiveCategory).where(ArchiveCategory.code == item["code"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  skip existing: {item['code']}")
            continue
        cat = ArchiveCategory(
            code=item["code"],
            name=item["name"],
            is_builtin=True,
            requires_privacy_guard=item["requires_privacy_guard"],
            parent_id=code_to_id.get(item["parent_id_code"]),
            field_schema=item["field_schema"] or None,
        )
        db.add(cat)
        await db.flush()
        print(f"  inserted: {item['code']} {item['name']}")

    await db.commit()
    print("Done.")


async def main() -> None:
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        await seed(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
