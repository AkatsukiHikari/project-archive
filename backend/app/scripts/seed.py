"""
幂等种子脚本 — 初始化系统必要基础数据

执行顺序：
  1. 默认租户 (system)
  2. 内置全局角色 (superadmin / admin / viewer)
  3. 完整菜单树
  4. 超级管理员用户
  5. 角色 ↔ 菜单绑定
  6. 用户 ↔ superadmin 角色绑定

幂等保证：所有实体以唯一业务键查重，已存在则跳过，不存在才插入。
手动执行：uv run python -m app.scripts.seed
"""

import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infra.db.session import AsyncSessionLocal
from app.modules.iam.models.tenant import Tenant, Organization
from app.modules.iam.models.user import User, Role
from app.modules.iam.models.permission import Menu
from app.core.security.password import get_password_hash
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── 菜单树定义 ──────────────────────────────────────────────────────────────
# type: DIR(目录) | MENU(菜单) | BUTTON(按钮)
MENU_TREE = [
    {
        "code": "platform",
        "name": "平台基础管理",
        "type": "DIR",
        "icon": "heroicons:server-stack",
        "sort_order": 10,
        "children": [
            {"code": "platform:tenants", "name": "租户管理",   "type": "MENU", "path": "/admin/tenants",       "icon": "heroicons:building-storefront", "sort_order": 1},
            {"code": "platform:orgs",    "name": "组织架构",   "type": "MENU", "path": "/admin/organizations", "icon": "heroicons:building-office-2",   "sort_order": 2},
            {"code": "platform:users",   "name": "用户管理",   "type": "MENU", "path": "/admin/users",         "icon": "heroicons:users",               "sort_order": 3},
            {"code": "platform:roles",   "name": "角色与权限", "type": "MENU", "path": "/admin/roles",         "icon": "heroicons:shield-check",        "sort_order": 4},
            {"code": "platform:menus",   "name": "菜单与权限", "type": "MENU", "path": "/admin/menus",         "icon": "heroicons:list-bullet",         "sort_order": 5},
        ],
    },
    {
        "code": "security",
        "name": "安全与集成",
        "type": "DIR",
        "icon": "heroicons:lock-closed",
        "sort_order": 20,
        "children": [
            {"code": "security:sso",   "name": "SSO 集成", "type": "MENU", "path": "/admin/sso",   "icon": "heroicons:key",                    "sort_order": 1},
            {"code": "security:audit", "name": "审计日志", "type": "MENU", "path": "/admin/audit", "icon": "heroicons:clipboard-document-list", "sort_order": 2},
        ],
    },
    {
        "code": "archive",
        "name": "档案管理",
        "type": "DIR",
        "icon": "heroicons:archive-box",
        "sort_order": 30,
        "children": [
            # ── 档案收集 ──────────────────────────────────────────────────────────
            {
                "code": "archive.collection", "name": "档案收集", "type": "DIR",
                "icon": "heroicons:inbox-arrow-down", "sort_order": 1,
                "children": [
                    {"code": "archive.collection.transfer",   "name": "归档移交", "type": "MENU", "path": "/archive/collection/transfer",  "icon": "heroicons:arrow-down-tray",          "sort_order": 1},
                    {"code": "archive.collection.receive",    "name": "接收登记", "type": "MENU", "path": "/archive/collection/receive",   "icon": "heroicons:clipboard-document-check", "sort_order": 2},
                    {"code": "archive.collection.import",     "name": "批量导入", "type": "MENU", "path": "/archive/collection/import",    "icon": "heroicons:table-cells",              "sort_order": 3},
                    {"code": "archive.collection.ledger",     "name": "收集台账", "type": "MENU", "path": "/archive/collection/ledger",    "icon": "heroicons:book-open",                "sort_order": 4},
                ],
            },
            # ── 档案整理 ──────────────────────────────────────────────────────────
            {
                "code": "archive.organize", "name": "档案整理", "type": "DIR",
                "icon": "heroicons:pencil-square", "sort_order": 2,
                "children": [
                    {"code": "archive.organize.records",  "name": "档案著录",   "type": "MENU", "path": "/archive/organize/records",  "icon": "heroicons:document-text",       "sort_order": 1},
                    {"code": "archive.organize.catalogs", "name": "目录管理",   "type": "MENU", "path": "/archive/organize/catalogs", "icon": "heroicons:bars-3-bottom-left",  "sort_order": 2},
                    {"code": "archive.organize.digitize", "name": "数字化加工", "type": "MENU", "path": "/archive/organize/digitize", "icon": "heroicons:computer-desktop",    "sort_order": 3},
                    {"code": "archive.organize.ledger",   "name": "整理台账",   "type": "MENU", "path": "/archive/organize/ledger",   "icon": "heroicons:book-open",           "sort_order": 4},
                ],
            },
            # ── 档案保管 ──────────────────────────────────────────────────────────
            {
                "code": "archive.storage", "name": "档案保管", "type": "DIR",
                "icon": "heroicons:building-library", "sort_order": 3,
                "children": [
                    {"code": "archive.storage.vault",     "name": "库房管理",   "type": "MENU", "path": "/archive/storage/vault",     "icon": "heroicons:home-modern",          "sort_order": 1},
                    {"code": "archive.storage.inout",     "name": "出入库记录", "type": "MENU", "path": "/archive/storage/inout",     "icon": "heroicons:arrows-right-left",    "sort_order": 2},
                    {"code": "archive.storage.detection", "name": "四性检测",   "type": "MENU", "path": "/archive/storage/detection", "icon": "heroicons:shield-check",         "sort_order": 3},
                    {"code": "archive.storage.repair",    "name": "档案修复",   "type": "MENU", "path": "/archive/storage/repair",    "icon": "heroicons:wrench-screwdriver",   "sort_order": 4},
                    {"code": "archive.storage.ledger",    "name": "保管台账",   "type": "MENU", "path": "/archive/storage/ledger",    "icon": "heroicons:book-open",            "sort_order": 5},
                ],
            },
            # ── 档案利用 ──────────────────────────────────────────────────────────
            {
                "code": "archive.utilization", "name": "档案利用", "type": "DIR",
                "icon": "heroicons:magnifying-glass-circle", "sort_order": 4,
                "children": [
                    {"code": "archive.utilization.apply",       "name": "利用申请", "type": "MENU", "path": "/archive/utilization/apply",       "icon": "heroicons:document-plus",       "sort_order": 1},
                    {"code": "archive.utilization.reading",     "name": "查阅登记", "type": "MENU", "path": "/archive/utilization/reading",     "icon": "heroicons:eye",                 "sort_order": 2},
                    {"code": "archive.utilization.borrow",      "name": "借阅管理", "type": "MENU", "path": "/archive/utilization/borrow",      "icon": "heroicons:arrow-uturn-right",   "sort_order": 3},
                    {"code": "archive.utilization.copy",        "name": "复制申请", "type": "MENU", "path": "/archive/utilization/copy",        "icon": "heroicons:document-duplicate",  "sort_order": 4},
                    {"code": "archive.utilization.certificate", "name": "证明开具", "type": "MENU", "path": "/archive/utilization/certificate", "icon": "heroicons:identification",      "sort_order": 5},
                    {"code": "archive.utilization.ledger",      "name": "利用台账", "type": "MENU", "path": "/archive/utilization/ledger",      "icon": "heroicons:book-open",           "sort_order": 6},
                ],
            },
            # ── 档案鉴定 ──────────────────────────────────────────────────────────
            {
                "code": "archive.appraisal", "name": "档案鉴定", "type": "DIR",
                "icon": "heroicons:scale", "sort_order": 5,
                "children": [
                    {"code": "archive.appraisal.plan",            "name": "鉴定计划", "type": "MENU", "path": "/archive/appraisal/plan",            "icon": "heroicons:calendar",                "sort_order": 1},
                    {"code": "archive.appraisal.review",          "name": "期限复查", "type": "MENU", "path": "/archive/appraisal/review",          "icon": "heroicons:clock",                   "sort_order": 2},
                    {"code": "archive.appraisal.evaluate",        "name": "鉴定工作", "type": "MENU", "path": "/archive/appraisal/evaluate",        "icon": "heroicons:clipboard-document-list", "sort_order": 3},
                    {"code": "archive.appraisal.destroy-apply",   "name": "销毁申请", "type": "MENU", "path": "/archive/appraisal/destroy-apply",   "icon": "heroicons:trash",                   "sort_order": 4},
                    {"code": "archive.appraisal.destroy-approve", "name": "销毁审批", "type": "MENU", "path": "/archive/appraisal/destroy-approve", "icon": "heroicons:check-badge",             "sort_order": 5},
                    {"code": "archive.appraisal.destroy-exec",    "name": "销毁执行", "type": "MENU", "path": "/archive/appraisal/destroy-exec",    "icon": "heroicons:fire",                    "sort_order": 6},
                    {"code": "archive.appraisal.ledger",          "name": "鉴定台账", "type": "MENU", "path": "/archive/appraisal/ledger",          "icon": "heroicons:book-open",               "sort_order": 7},
                ],
            },
            # ── 档案编研 ──────────────────────────────────────────────────────────
            {
                "code": "archive.research", "name": "档案编研", "type": "DIR",
                "icon": "heroicons:academic-cap", "sort_order": 6,
                "children": [
                    {"code": "archive.research.project",     "name": "编研项目", "type": "MENU", "path": "/archive/research/project",     "icon": "heroicons:folder-open",       "sort_order": 1},
                    {"code": "archive.research.compilation", "name": "专题汇编", "type": "MENU", "path": "/archive/research/compilation", "icon": "heroicons:book-open",         "sort_order": 2},
                    {"code": "archive.research.stats",       "name": "档案统计", "type": "MENU", "path": "/archive/research/stats",       "icon": "heroicons:chart-bar",         "sort_order": 3},
                    {"code": "archive.research.annual",      "name": "年报管理", "type": "MENU", "path": "/archive/research/annual",      "icon": "heroicons:document-chart-bar", "sort_order": 4},
                ],
            },
            # ── 基础配置 ──────────────────────────────────────────────────────────
            {
                "code": "archive.settings", "name": "基础配置", "type": "DIR",
                "icon": "heroicons:cog-6-tooth", "sort_order": 7,
                "children": [
                    {"code": "archive.settings.fonds",      "name": "全宗管理",   "type": "MENU", "path": "/archive/settings/fonds",      "icon": "heroicons:building-library", "sort_order": 1},
                    {"code": "archive.settings.categories", "name": "档案门类",   "type": "MENU", "path": "/archive/settings/categories", "icon": "heroicons:tag",              "sort_order": 2},
                    {"code": "archive.settings.norules",    "name": "档号规则",   "type": "MENU", "path": "/archive/settings/norules",    "icon": "heroicons:hashtag",          "sort_order": 3},
                    {"code": "archive.settings.retention",  "name": "保管期限表", "type": "MENU", "path": "/archive/settings/retention",  "icon": "heroicons:calendar-days",    "sort_order": 4},
                    {"code": "archive.settings.metadata",   "name": "元数据方案", "type": "MENU", "path": "/archive/settings/metadata",   "icon": "heroicons:variable",         "sort_order": 5},
                ],
            },
        ],
    },
    {
        "code": "ai",
        "name": "AI 智能功能",
        "type": "DIR",
        "icon": "heroicons:sparkles",
        "sort_order": 40,
        "children": [
            {"code": "ai:chat",      "name": "AI 对话助手", "type": "MENU", "path": "/ai",           "icon": "heroicons:chat-bubble-left-ellipsis", "sort_order": 1},
            {"code": "ai:knowledge", "name": "知识库管理",  "type": "MENU", "path": "/ai/knowledge", "icon": "heroicons:book-open",                "sort_order": 2},
        ],
    },
]


# ── 工具函数 ─────────────────────────────────────────────────────────────────

async def _get_or_none(db: AsyncSession, model, **filters):
    """按字段查询单条记录，不存在返回 None。"""
    stmt = select(model).filter_by(**filters)
    result = await db.execute(stmt)
    return result.scalars().first()


async def _ensure_tenant(db: AsyncSession) -> Tenant:
    tenant = await _get_or_none(db, Tenant, code="system", is_deleted=False)
    if tenant:
        logger.info("seed: 默认租户已存在，跳过")
        return tenant

    tenant = Tenant(
        code="system",
        name="系统默认租户",
        description="系统内置默认租户，不可删除",
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    logger.info("seed: 创建默认租户 [system]")
    return tenant


async def _ensure_roles(db: AsyncSession) -> dict[str, Role]:
    """确保三个内置全局角色存在，返回 {code: Role} 字典。"""
    role_defs = [
        {"code": "superadmin", "name": "超级管理员", "description": "拥有系统全部权限，不可删除"},
        {"code": "admin",      "name": "系统管理员", "description": "拥有平台管理权限"},
        {"code": "viewer",     "name": "只读用户",   "description": "仅可查看，不可操作"},
    ]
    roles: dict[str, Role] = {}
    for rd in role_defs:
        role = await _get_or_none(db, Role, code=rd["code"], is_deleted=False)
        if not role:
            role = Role(
                code=rd["code"],
                name=rd["name"],
                description=rd["description"],
                tenant_id=None,  # 全局角色
            )
            db.add(role)
            await db.flush()
            logger.info("seed: 创建角色 [%s]", rd["code"])
        else:
            logger.info("seed: 角色 [%s] 已存在，跳过", rd["code"])
        roles[rd["code"]] = role
    return roles


async def _ensure_menus(
    db: AsyncSession,
    tree: list,
    parent_id: Optional[uuid.UUID] = None,
) -> list[Menu]:
    """递归确保菜单树，返回所有叶子+目录 Menu 对象列表。"""
    all_menus: list[Menu] = []
    for node in tree:
        menu = await _get_or_none(db, Menu, code=node["code"], is_deleted=False)
        if not menu:
            menu = Menu(
                code=node["code"],
                name=node["name"],
                type=node["type"],
                path=node.get("path"),
                icon=node.get("icon"),
                sort_order=node.get("sort_order", 0),
                is_visible=True,
                parent_id=parent_id,
            )
            db.add(menu)
            await db.flush()
            logger.info("seed: 创建菜单 [%s] %s", node["type"], node["code"])
        else:
            updated = False
            if menu.icon != node.get("icon"):
                menu.icon = node.get("icon")
                updated = True
            if menu.name != node["name"]:
                menu.name = node["name"]
                updated = True
            if updated:
                logger.info("seed: 更新菜单 [%s] 字段", node["code"])
            else:
                logger.info("seed: 菜单 [%s] 已存在，跳过", node["code"])
        all_menus.append(menu)
        if node.get("children"):
            all_menus.extend(
                await _ensure_menus(db, node["children"], parent_id=menu.id)
            )
    return all_menus


async def _bind_role_menus(
    db: AsyncSession,
    role: Role,
    menus: list[Menu],
) -> None:
    """将菜单列表绑定到角色（追加方式，不覆盖已有绑定）。"""
    # 重新加载带 menus 关系的 role
    result = await db.execute(
        select(Role).options(selectinload(Role.menus)).where(Role.id == role.id)
    )
    role = result.scalars().first()
    existing_ids = {m.id for m in role.menus}
    added = 0
    for menu in menus:
        if menu.id not in existing_ids:
            role.menus.append(menu)
            added += 1
    if added:
        logger.info("seed: 角色 [%s] 绑定 %d 条菜单", role.code, added)


async def _ensure_superadmin(
    db: AsyncSession,
    tenant: Tenant,
    superadmin_role: Role,
) -> User:
    """确保超级管理员用户存在，且已绑定 superadmin 角色。"""
    user = await _get_or_none(db, User, username="admin", is_deleted=False)

    if not user:
        password = settings.ADMIN_PASSWORD
        if not password:
            raise RuntimeError(
                "ADMIN_PASSWORD 未配置！请在 backend/.env 中设置 ADMIN_PASSWORD=<密码>"
            )
        user = User(
            username="admin",
            email=settings.ADMIN_EMAIL,
            hashed_password=get_password_hash(password),
            full_name="超级管理员",
            is_active=True,
            is_superadmin=True,
            tenant_id=tenant.id,
        )
        db.add(user)
        await db.flush()
        logger.info("seed: 创建超级管理员 [admin]，邮箱 %s", settings.ADMIN_EMAIL)

    # 重新加载带 roles 关系的用户，确保角色绑定存在（幂等）
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user.id)
    )
    user = result.scalars().first()
    if superadmin_role.id not in {r.id for r in user.roles}:
        user.roles.append(superadmin_role)
        logger.info("seed: 超级管理员 [admin] 绑定 superadmin 角色")
    else:
        logger.info("seed: 超级管理员 [admin] 已存在，角色绑定正常，跳过")
    return user


# ── 入口 ─────────────────────────────────────────────────────────────────────

async def run_seed() -> None:
    """执行完整种子流程（幂等）。"""
    if getattr(settings, "SKIP_SEED", False):
        logger.info("seed: SKIP_SEED=true，跳过初始化")
        return

    logger.info("seed: 开始初始化基础数据…")
    async with AsyncSessionLocal() as db:
        async with db.begin():
            # 1. 默认租户
            tenant = await _ensure_tenant(db)

            # 2. 内置角色
            roles = await _ensure_roles(db)

            # 3. 完整菜单树
            all_menus = await _ensure_menus(db, MENU_TREE)

            # 4. superadmin 角色绑定所有菜单
            await _bind_role_menus(db, roles["superadmin"], all_menus)

            # 5. admin 角色绑定平台管理+安全菜单（非档案/AI业务菜单）
            admin_menus = [m for m in all_menus if m.code.startswith(("platform", "security"))]
            await _bind_role_menus(db, roles["admin"], admin_menus)

            # 6. 超级管理员用户
            await _ensure_superadmin(db, tenant, roles["superadmin"])

    logger.info("seed: 基础数据初始化完成 ✓")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(run_seed())
