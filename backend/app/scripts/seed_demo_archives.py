"""
演示档案数据种子（3 个全宗 + 1 个案卷目录 + 60 条 ArchiveStaging + ES 同步）

跑完后：
- 前端"档案著录"页可直接查询
- AI 问答 / 检索能命中真实档案
- /admin/ai/audit 看到搜索行为

运行::

    cd backend && uv run python -m app.scripts.seed_demo_archives
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import AsyncSessionLocal
from app.modules.iam.models.tenant import Tenant
from app.modules.repository.models.archive import ArchiveStaging, Catalog
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.fonds import Fonds
from app.modules.repository.services import es_sync_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# 全宗 ───────────────────────────────────────────────────────────────────
FONDS = [
    {
        "code": "J001",
        "name": "坤爵市档案馆机关全宗",
        "short_name": "市档案馆",
        "description": "市档案馆本机关历史档案集合，涵盖办公文书、人事、会议纪要等",
        "start_year": 2000,
        "end_year": None,
        "retention_period": "permanent",
    },
    {
        "code": "Q001",
        "name": "坤爵财务管理中心",
        "short_name": "财务中心",
        "description": "市财务管理中心账目凭证、预决算、审计报告",
        "start_year": 2018,
        "end_year": None,
        "retention_period": "permanent",
    },
    {
        "code": "Q002",
        "name": "坤爵人力资源服务中心",
        "short_name": "人力中心",
        "description": "市人事档案、聘任、晋升、奖惩、培训",
        "start_year": 2010,
        "end_year": None,
        "retention_period": "permanent",
    },
]


# 60 条档案数据 ──────────────────────────────────────────────────────────
# 字段约定：(QZH, category_code, ND, MJ, BGQX, TM, RZZ, WJRQ)
# MJ: public / internal / secret
# BGQX: permanent / long / short
ARCHIVES = [
    # ── 文书档案（机关全宗 J001）20 条 ─────────────────────────────────
    ("J001", "WS", 2020, "public",   "permanent", "关于成立信息化建设领导小组的通知", "办公室",        "2020-03-15"),
    ("J001", "WS", 2020, "public",   "permanent", "2020 年度工作总结",                "档案馆",         "2020-12-28"),
    ("J001", "WS", 2021, "public",   "long",      "2021 年度档案管理工作要点",        "档案馆",         "2021-01-10"),
    ("J001", "WS", 2021, "internal", "long",      "2021 年信访工作专题汇报",          "信访科",         "2021-06-20"),
    ("J001", "WS", 2022, "public",   "permanent", "市档案馆数字化建设三年规划",        "技术科",         "2022-04-08"),
    ("J001", "WS", 2022, "internal", "long",      "2022 年党建工作部署会议纪要",       "党办",           "2022-02-25"),
    ("J001", "WS", 2023, "public",   "permanent", "关于全市档案系统升级改造的实施方案", "档案馆 / 信息中心", "2023-05-12"),
    ("J001", "WS", 2023, "public",   "permanent", "2023 年度档案利用工作报告",         "档案利用科",      "2023-12-30"),
    ("J001", "WS", 2023, "internal", "long",      "2023 年内部审计整改报告",          "审计科",         "2023-09-15"),
    ("J001", "WS", 2024, "public",   "permanent", "市档案馆 2024 年度财政预算编制说明", "财务科",         "2024-01-25"),
    ("J001", "WS", 2024, "public",   "long",      "档案保管期限表修订说明",            "鉴定科",         "2024-03-18"),
    ("J001", "WS", 2024, "internal", "short",     "2024 年度信息化设备采购清单",       "技术科",         "2024-05-20"),
    ("J001", "WS", 2024, "public",   "permanent", "全市档案馆建设标准化检查通报",       "档案馆",         "2024-07-22"),
    ("J001", "WS", 2024, "secret",   "permanent", "重要档案目录涉密复审情况报告",       "保密办",         "2024-08-08"),
    ("J001", "WS", 2025, "public",   "permanent", "2025 年档案宣传月活动方案",         "宣传科",         "2025-04-10"),
    ("J001", "WS", 2025, "public",   "long",      "档案修复实验室建设方案",            "技术科",         "2025-05-15"),
    ("J001", "WS", 2025, "internal", "short",     "2025 年第二季度工作督查情况",       "督查办",         "2025-07-01"),
    ("J001", "WS", 2026, "public",   "permanent", "市档案馆 2026 年信息化升级招标公告", "技术科 / 财务科",  "2026-01-15"),
    ("J001", "WS", 2026, "public",   "long",      "2026 年第一季度档案接收登记汇总",   "档案利用科",      "2026-04-02"),
    ("J001", "WS", 2026, "internal", "long",      "2026 年党风廉政建设专题会议纪要",    "党办",           "2026-03-28"),

    # ── 会计档案（财务中心 Q001）20 条 ──────────────────────────────────
    ("Q001", "HJ", 2020, "internal", "long",      "2020 年度年终决算报告",            "财务部",         "2021-01-28"),
    ("Q001", "HJ", 2020, "internal", "short",     "2020 年第四季度银行对账单合订",      "财务部",         "2021-01-10"),
    ("Q001", "HJ", 2021, "internal", "long",      "2021 年度财务审计报告",            "审计科 / 财务部", "2022-02-15"),
    ("Q001", "HJ", 2021, "internal", "short",     "2021 年差旅费报销凭证汇编",         "财务部",         "2021-12-30"),
    ("Q001", "HJ", 2021, "internal", "short",     "2021 年办公用品采购发票合订",       "财务部",         "2021-12-31"),
    ("Q001", "HJ", 2022, "internal", "long",      "2022 年度财务凭证（一）月份合订本",  "财务部",         "2022-02-10"),
    ("Q001", "HJ", 2022, "internal", "long",      "2022 年度财务凭证（二）月份合订本",  "财务部",         "2022-03-05"),
    ("Q001", "HJ", 2022, "internal", "long",      "2022 年度财务凭证（年中）合订本",   "财务部",         "2022-07-08"),
    ("Q001", "HJ", 2023, "internal", "long",      "2023 年度财务凭证（一季度）合订本",  "财务部",         "2023-04-15"),
    ("Q001", "HJ", 2023, "internal", "long",      "2023 年度财务凭证（二季度）合订本",  "财务部",         "2023-07-20"),
    ("Q001", "HJ", 2023, "internal", "long",      "2023 年度财务凭证（三季度）合订本",  "财务部",         "2023-10-18"),
    ("Q001", "HJ", 2023, "internal", "long",      "2023 年度财务凭证（四季度）合订本",  "财务部",         "2024-01-15"),
    ("Q001", "HJ", 2024, "internal", "long",      "2024 年度财务凭证（一季度）合订本",  "财务部",         "2024-04-12"),
    ("Q001", "HJ", 2024, "internal", "long",      "2024 年度财务凭证（二季度）合订本",  "财务部",         "2024-07-22"),
    ("Q001", "HJ", 2024, "internal", "long",      "2024 年度财务凭证（三季度）合订本",  "财务部",         "2024-10-25"),
    ("Q001", "HJ", 2024, "internal", "long",      "2024 年度财务凭证（四季度）合订本",  "财务部",         "2025-01-20"),
    ("Q001", "HJ", 2025, "internal", "long",      "2025 年度财务凭证（一季度）合订本",  "财务部",         "2025-04-15"),
    ("Q001", "HJ", 2025, "internal", "long",      "2025 年度财务凭证（二季度）合订本",  "财务部",         "2025-07-12"),
    ("Q001", "HJ", 2026, "internal", "long",      "2026 年度财务凭证（一季度）合订本",  "财务部",         "2026-04-10"),
    ("Q001", "HJ", 2026, "internal", "long",      "2026 年度预算编制说明（部门汇总）",  "财务部 / 综合科", "2026-02-28"),

    # ── 人事档案（人力中心 Q002）20 条 ──────────────────────────────────
    ("Q002", "ZY_RS", 2020, "secret",   "permanent", "2020 年度处级干部任免审批材料",   "人事科",     "2020-09-30"),
    ("Q002", "ZY_RS", 2020, "internal", "long",      "2020 年度新进员工入职登记表合订", "人事科",     "2020-11-15"),
    ("Q002", "ZY_RS", 2021, "secret",   "permanent", "2021 年度科级干部考核结果汇总",    "人事科 / 党组", "2022-01-20"),
    ("Q002", "ZY_RS", 2021, "internal", "long",      "2021 年度业务培训记录",          "培训科",     "2021-12-15"),
    ("Q002", "ZY_RS", 2022, "internal", "permanent", "2022 年度劳动合同签订情况汇总",    "人事科",     "2022-06-30"),
    ("Q002", "ZY_RS", 2022, "secret",   "permanent", "2022 年度专业技术职务评聘材料",    "人事科 / 评委会", "2022-11-08"),
    ("Q002", "ZY_RS", 2022, "internal", "long",      "2022 年度员工奖励决定汇总",       "人事科",     "2022-12-31"),
    ("Q002", "ZY_RS", 2023, "secret",   "permanent", "2023 年度干部任免审批材料",       "人事科",     "2023-10-12"),
    ("Q002", "ZY_RS", 2023, "internal", "long",      "2023 年度员工晋升档案",          "人事科",     "2023-12-18"),
    ("Q002", "ZY_RS", 2023, "internal", "long",      "2023 年度新员工试用期考核",       "人事科",     "2023-09-25"),
    ("Q002", "ZY_RS", 2024, "internal", "permanent", "2024 年度员工花名册（更新版）",    "人事科",     "2024-12-30"),
    ("Q002", "ZY_RS", 2024, "secret",   "permanent", "2024 年度科以上干部任免文件",      "人事科 / 党组", "2024-11-15"),
    ("Q002", "ZY_RS", 2024, "internal", "long",      "2024 年度专技人员继续教育记录",    "培训科",     "2024-12-15"),
    ("Q002", "ZY_RS", 2024, "internal", "long",      "2024 年度劳动合同续签情况汇总",    "人事科",     "2024-06-30"),
    ("Q002", "ZY_RS", 2024, "internal", "short",     "2024 年度职工请假记录归档",       "人事科",     "2024-12-31"),
    ("Q002", "ZY_RS", 2025, "secret",   "permanent", "2025 年度干部考核结果",          "人事科 / 党组", "2026-01-10"),
    ("Q002", "ZY_RS", 2025, "internal", "long",      "2025 年度员工奖惩决定汇总",       "人事科",     "2025-12-28"),
    ("Q002", "ZY_RS", 2025, "internal", "permanent", "2025 年度人才引进材料",          "人事科",     "2025-08-15"),
    ("Q002", "ZY_RS", 2026, "internal", "long",      "2026 年第一季度员工入职登记",     "人事科",     "2026-04-05"),
    ("Q002", "ZY_RS", 2026, "internal", "long",      "2026 年度专业技术岗位评聘启动方案", "人事科 / 评委会", "2026-03-20"),
]


async def _get_or_create_fonds(
    db: AsyncSession, tenant_id: uuid.UUID, code: str, **fields
) -> Fonds:
    stmt = select(Fonds).where(Fonds.fonds_code == code, Fonds.is_deleted.is_(False))
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing
    row = Fonds(
        fonds_code=code,
        tenant_id=tenant_id,
        status="active",
        **fields,
    )
    db.add(row)
    await db.flush()
    logger.info("创建全宗 %s — %s", code, fields.get("name"))
    return row


async def _ensure_default_catalog(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    fonds_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Catalog:
    catalog_no = f"DEMO-{fonds_id.hex[:6]}-{category_id.hex[:6]}"
    stmt = select(Catalog).where(
        Catalog.catalog_no == catalog_no, Catalog.is_deleted.is_(False)
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing
    row = Catalog(
        fonds_id=fonds_id,
        category_id=category_id,
        catalog_no=catalog_no,
        name="演示目录（一文一件）",
        catalog_type="yi_wen_yi_jian",
        tenant_id=tenant_id,
    )
    db.add(row)
    await db.flush()
    return row


def _build_dh(qzh: str, cat_code: str, nd: int, bgqx: str, seq: int) -> str:
    bgqx_letter = {"permanent": "Y", "long": "C", "short": "D"}.get(bgqx, "Y")
    return f"{qzh}-{cat_code}-{nd}-{bgqx_letter}-{seq:05d}"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.code == "system"))
        ).scalar_one_or_none()
        if tenant is None:
            logger.error("默认租户不存在，先跑 seed.py")
            return

        # 1. 全宗
        fonds_by_code: dict[str, Fonds] = {}
        for f in FONDS:
            row = await _get_or_create_fonds(
                db,
                tenant_id=tenant.id,
                code=f["code"],
                name=f["name"],
                short_name=f["short_name"],
                description=f["description"],
                start_year=f["start_year"],
                end_year=f["end_year"],
                retention_period=f["retention_period"],
            )
            fonds_by_code[f["code"]] = row
        await db.commit()

        # 2. 类目
        cat_stmt = select(ArchiveCategory).where(ArchiveCategory.is_deleted.is_(False))
        cats = (await db.execute(cat_stmt)).scalars().all()
        cat_by_code: dict[str, ArchiveCategory] = {c.code: c for c in cats}
        if not cat_by_code:
            logger.error("档案类目不存在，先跑 seed_archive_categories.py")
            return

        # 3. 档案（幂等：(QZH, TM) 唯一）
        seq_counter: dict[tuple[str, int, str], int] = {}
        inserted = 0
        skipped = 0
        new_rows: list[ArchiveStaging] = []

        for qzh, cat_code, nd, mj, bgqx, tm, rzz, wjrq in ARCHIVES:
            # 幂等：先按 TM 查
            stmt = select(ArchiveStaging).where(
                ArchiveStaging.QZH == qzh,
                ArchiveStaging.TM == tm,
                ArchiveStaging.is_deleted.is_(False),
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                skipped += 1
                continue

            fonds = fonds_by_code.get(qzh)
            category = cat_by_code.get(cat_code)
            if fonds is None or category is None:
                logger.warning("跳过：缺全宗或类目 qzh=%s cat=%s", qzh, cat_code)
                continue

            catalog = await _ensure_default_catalog(
                db,
                tenant_id=tenant.id,
                fonds_id=fonds.id,
                category_id=category.id,
            )

            key = (qzh, nd, bgqx)
            seq_counter[key] = seq_counter.get(key, 0) + 1
            dh = _build_dh(qzh, cat_code, nd, bgqx, seq_counter[key])

            row = ArchiveStaging(
                fonds_id=fonds.id,
                catalog_id=catalog.id,
                category_id=category.id,
                tenant_id=tenant.id,
                DH=dh,
                QZH=qzh,
                TM=tm,
                RZZ=rzz,
                ND=nd,
                WJRQ=wjrq,
                YS=1,
                MJ=mj,
                BGQX=bgqx,
                status="archived",
                ext_fields={
                    "seeded_by": "seed_demo_archives",
                    "seeded_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(row)
            new_rows.append(row)
            inserted += 1

        await db.commit()
        # 4. 同步 ES（bulk）
        if new_rows:
            try:
                ok = await es_sync_service.bulk_sync(new_rows)
                logger.info("ES 同步成功 %d / 提交 %d 条", ok, len(new_rows))
            except Exception as exc:
                logger.error("ES 同步失败：%s", exc)

        logger.info("演示档案种子完成 ✓ 总计=%d 新增=%d 跳过=%d", len(ARCHIVES), inserted, skipped)


if __name__ == "__main__":
    asyncio.run(main())
