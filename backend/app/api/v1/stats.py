"""
管理后台统计 API

端点：
- GET /v1/stats/dashboard       — 仪表盘 KPI 摘要（含存储层关键指标）
- GET /v1/stats/storage         — 各存储组件详情 + 健康状态（超管）
- GET /v1/stats/platform-config — 平台配置状态（超管）
- GET /v1/stats/user-activity   — 近 N 天登录趋势（保留供其他页面使用）
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import cast, Date, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.response import ResponseModel, fail, success
from app.infra.db.session import get_db
from app.modules.audit.models import AuditLog
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.permission import Menu
from app.modules.iam.models.tenant import Organization, Tenant
from app.modules.iam.models.user import Role, User

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── 响应模型 ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    """顶部 KPI 卡片数据"""
    active_tenants: int       # 超管：全平台；非超管：-1（隐藏）
    total_users: int
    active_users: int
    total_roles: int          # 超管：全局角色数；非超管：-1
    total_orgs: int
    new_users_today: int
    # 存储层 KPI（超管可见，非超管为 -1）
    minio_objects: int        # MinIO 对象总数（-1 = 不可用/无权限）
    minio_size_gb: float      # MinIO 已用容量 GB
    pg_connections: int       # PostgreSQL 活跃连接数
    redis_memory_mb: float    # Redis 内存占用 MB


class MetricItem(BaseModel):
    label: str
    value: str


class BucketStat(BaseModel):
    name: str
    object_count: int
    size_mb: float


class StorageComponent(BaseModel):
    """单个存储组件的完整状态 + 指标"""
    name: str                              # 显示名称
    type: str                              # postgres / redis / rabbitmq / minio / elasticsearch
    status: str                            # "ok" | "error" | "unknown"
    latency_ms: float
    summary: str                           # 一行摘要文字
    metrics: list[MetricItem]              # 详细指标列表
    chart_data: list[BucketStat] | None = None  # MinIO 专用：各桶分布


class StorageOverviewResponse(BaseModel):
    components: list[StorageComponent]
    checked_at: datetime


class PlatformConfigResponse(BaseModel):
    storage_type: str
    total_menus: int
    total_buttons: int
    total_menu_visible: int
    total_roles: int
    total_tenants: int


class DayActivity(BaseModel):
    date: str
    count: int


class UserActivityResponse(BaseModel):
    days: int
    data: list[DayActivity]


# ─── /dashboard ───────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=ResponseModel[DashboardStats], summary="仪表盘 KPI")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    is_super = current_user.is_superadmin

    # 租户数（仅超管）
    active_tenants = -1
    if is_super:
        active_tenants = (await db.execute(
            select(func.count()).select_from(Tenant).where(
                Tenant.is_deleted == False, Tenant.is_active == True
            )
        )).scalar_one()

    # 角色数（仅超管）
    total_roles = -1
    if is_super:
        total_roles = (await db.execute(
            select(func.count()).select_from(Role).where(Role.is_deleted == False)
        )).scalar_one()

    # 用户数
    user_base = select(func.count()).select_from(User).where(User.is_deleted == False)
    active_base = user_base.where(User.is_active == True)
    if not is_super and current_user.tenant_id:
        user_base = user_base.where(User.tenant_id == current_user.tenant_id)
        active_base = active_base.where(User.tenant_id == current_user.tenant_id)
    total_users = (await db.execute(user_base)).scalar_one()
    active_users = (await db.execute(active_base)).scalar_one()

    # 部门数
    org_base = select(func.count()).select_from(Organization).where(Organization.is_deleted == False)
    if not is_super and current_user.tenant_id:
        org_base = org_base.where(Organization.tenant_id == current_user.tenant_id)
    total_orgs = (await db.execute(org_base)).scalar_one()

    # 今日新增用户
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_stmt = select(func.count()).select_from(User).where(
        User.is_deleted == False, User.create_time >= today_start
    )
    if not is_super and current_user.tenant_id:
        new_stmt = new_stmt.where(User.tenant_id == current_user.tenant_id)
    new_users_today = (await db.execute(new_stmt)).scalar_one()

    # 存储层 KPI（超管，异步并发获取）
    minio_objects, minio_size_gb, pg_connections, redis_memory_mb = -1, -1.0, -1, -1.0
    if is_super:
        minio_stat, pg_stat, redis_stat = await asyncio.gather(
            _fetch_minio_kpi(),
            _fetch_pg_kpi(db),
            _fetch_redis_kpi(),
            return_exceptions=True,
        )
        if isinstance(minio_stat, dict):
            minio_objects = minio_stat.get("objects", -1)
            minio_size_gb = minio_stat.get("size_gb", -1.0)
        if isinstance(pg_stat, dict):
            pg_connections = pg_stat.get("connections", -1)
        if isinstance(redis_stat, dict):
            redis_memory_mb = redis_stat.get("memory_mb", -1.0)

    return success(data=DashboardStats(
        active_tenants=active_tenants,
        total_users=total_users,
        active_users=active_users,
        total_roles=total_roles,
        total_orgs=total_orgs,
        new_users_today=new_users_today,
        minio_objects=minio_objects,
        minio_size_gb=round(minio_size_gb, 2),
        pg_connections=pg_connections,
        redis_memory_mb=round(redis_memory_mb, 1),
    ).model_dump())


# ─── /storage ─────────────────────────────────────────────────────────────────

@router.get("/storage", response_model=ResponseModel[StorageOverviewResponse], summary="存储组件详情（超管）")
async def get_storage_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not current_user.is_superadmin:
        return fail(ErrorCode.FORBIDDEN, "无权限访问此接口")

    components = await asyncio.gather(
        _detail_postgres(db),
        _detail_redis(),
        _detail_minio(),
        _detail_elasticsearch(),
        _detail_rabbitmq(),
        return_exceptions=True,
    )

    results: list[StorageComponent] = []
    for c in components:
        if isinstance(c, StorageComponent):
            results.append(c)
        else:
            logger.warning("存储组件检查异常: %s", c)

    return success(data=StorageOverviewResponse(
        components=results,
        checked_at=datetime.now(timezone.utc),
    ).model_dump())


# ─── /platform-config ─────────────────────────────────────────────────────────

@router.get("/platform-config", response_model=ResponseModel[PlatformConfigResponse], summary="平台配置状态（超管）")
async def get_platform_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not current_user.is_superadmin:
        return fail(ErrorCode.FORBIDDEN, "无权限访问此接口")

    from app.core.config import settings

    total_menus = (await db.execute(
        select(func.count()).select_from(Menu).where(Menu.is_deleted == False)
    )).scalar_one()
    total_buttons = (await db.execute(
        select(func.count()).select_from(Menu).where(Menu.is_deleted == False, Menu.type == "BUTTON")
    )).scalar_one()
    total_menu_visible = (await db.execute(
        select(func.count()).select_from(Menu).where(
            Menu.is_deleted == False, Menu.is_visible == True, Menu.type != "BUTTON"
        )
    )).scalar_one()
    total_roles = (await db.execute(
        select(func.count()).select_from(Role).where(Role.is_deleted == False)
    )).scalar_one()
    total_tenants = (await db.execute(
        select(func.count()).select_from(Tenant).where(Tenant.is_deleted == False)
    )).scalar_one()

    return success(data=PlatformConfigResponse(
        storage_type=settings.STORAGE_TYPE,
        total_menus=total_menus,
        total_buttons=total_buttons,
        total_menu_visible=total_menu_visible,
        total_roles=total_roles,
        total_tenants=total_tenants,
    ).model_dump())


# ─── /user-activity ──────────────────────────────────────────────────────────

@router.get("/user-activity", response_model=ResponseModel[UserActivityResponse], summary="近 N 天登录趋势")
async def get_user_activity(
    days: int = Query(7, ge=7, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            cast(AuditLog.create_time, Date).label("day"),
            func.count(distinct(AuditLog.user_id)).label("count"),
        )
        .where(AuditLog.action == "USER_LOGIN", AuditLog.create_time >= since)
        .group_by("day")
        .order_by("day")
    )
    if not current_user.is_superadmin and current_user.tenant_id:
        stmt = stmt.where(AuditLog.tenant_id == current_user.tenant_id)

    rows = (await db.execute(stmt)).all()
    row_map = {str(r.day): r.count for r in rows}
    data = [
        DayActivity(date=str((datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()),
                    count=row_map.get(str((datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).date()), 0))
        for i in range(days)
    ]
    return success(data=UserActivityResponse(days=days, data=data).model_dump())


# ─── KPI 快速获取（轻量，用于 dashboard 卡片）────────────────────────────────

async def _fetch_minio_kpi() -> dict:
    from app.core.config import settings
    from minio import Minio
    import asyncio

    def _sync() -> dict:
        endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        client = Minio(endpoint, access_key=settings.MINIO_ACCESS_KEY,
                       secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_SECURE)
        total_objects = 0
        total_bytes = 0
        for bucket in client.list_buckets():
            for obj in client.list_objects(bucket.name, recursive=True):
                total_objects += 1
                total_bytes += obj.size or 0
        return {"objects": total_objects, "size_gb": total_bytes / 1024 / 1024 / 1024}

    return await asyncio.to_thread(_sync)


async def _fetch_pg_kpi(db: AsyncSession) -> dict:
    result = await db.execute(
        text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
    )
    return {"connections": result.scalar_one()}


async def _fetch_redis_kpi() -> dict:
    from app.infra.cache.redis import redis_service
    info = await redis_service.redis.info("memory")
    return {"memory_mb": int(info.get("used_memory", 0)) / 1024 / 1024}


# ─── 各组件详情检查 ────────────────────────────────────────────────────────────

async def _detail_postgres(db: AsyncSession) -> StorageComponent:
    t0 = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.monotonic() - t0) * 1000

        conns = (await db.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        )).scalar_one()

        db_size_bytes = (await db.execute(
            text("SELECT pg_database_size(current_database())")
        )).scalar_one()
        db_size_mb = round(db_size_bytes / 1024 / 1024, 1)

        table_count = (await db.execute(
            text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
        )).scalar_one()

        return StorageComponent(
            name="PostgreSQL", type="postgres", status="ok",
            latency_ms=round(latency, 2),
            summary=f"连接 {conns} 个 / {db_size_mb} MB / {table_count} 张表",
            metrics=[
                MetricItem(label="活跃连接数", value=f"{conns} 个"),
                MetricItem(label="数据库大小", value=f"{db_size_mb} MB"),
                MetricItem(label="数据表数量", value=f"{table_count} 张"),
            ],
        )
    except Exception as e:
        return StorageComponent(name="PostgreSQL", type="postgres", status="error",
                                latency_ms=0, summary=str(e), metrics=[])


async def _detail_redis() -> StorageComponent:
    from app.infra.cache.redis import redis_service
    t0 = time.monotonic()
    try:
        await redis_service.redis.ping()
        latency = (time.monotonic() - t0) * 1000

        mem_info = await redis_service.redis.info("memory")
        stats_info = await redis_service.redis.info("stats")
        key_count = await redis_service.redis.dbsize()

        used_mb = round(int(mem_info.get("used_memory", 0)) / 1024 / 1024, 1)
        peak_mb = round(int(mem_info.get("used_memory_peak", 0)) / 1024 / 1024, 1)
        hits = int(stats_info.get("keyspace_hits", 0))
        misses = int(stats_info.get("keyspace_misses", 0))
        hit_rate = round(hits / (hits + misses) * 100, 1) if (hits + misses) > 0 else 0.0

        return StorageComponent(
            name="Redis", type="redis", status="ok",
            latency_ms=round(latency, 2),
            summary=f"内存 {used_mb} MB / {key_count} 个 Key / 命中率 {hit_rate}%",
            metrics=[
                MetricItem(label="内存占用", value=f"{used_mb} MB"),
                MetricItem(label="内存峰值", value=f"{peak_mb} MB"),
                MetricItem(label="Key 数量", value=f"{key_count} 个"),
                MetricItem(label="命中率", value=f"{hit_rate}%"),
            ],
        )
    except Exception as e:
        return StorageComponent(name="Redis", type="redis", status="error",
                                latency_ms=0, summary=str(e), metrics=[])


async def _detail_minio() -> StorageComponent:
    from app.core.config import settings
    from minio import Minio

    t0 = time.monotonic()
    try:
        def _sync():
            endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
            client = Minio(endpoint, access_key=settings.MINIO_ACCESS_KEY,
                           secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_SECURE)
            buckets = client.list_buckets()
            result = []
            for b in buckets:
                obj_count = 0
                size_bytes = 0
                for obj in client.list_objects(b.name, recursive=True):
                    obj_count += 1
                    size_bytes += obj.size or 0
                result.append(BucketStat(
                    name=b.name,
                    object_count=obj_count,
                    size_mb=round(size_bytes / 1024 / 1024, 2),
                ))
            return result

        bucket_stats: list[BucketStat] = await asyncio.to_thread(_sync)
        latency = (time.monotonic() - t0) * 1000

        total_objects = sum(b.object_count for b in bucket_stats)
        total_mb = sum(b.size_mb for b in bucket_stats)
        total_gb = round(total_mb / 1024, 2) if total_mb >= 1024 else None
        size_display = f"{total_gb} GB" if total_gb else f"{round(total_mb, 1)} MB"

        return StorageComponent(
            name="MinIO 对象存储", type="minio", status="ok",
            latency_ms=round(latency, 2),
            summary=f"{len(bucket_stats)} 个存储桶 / {total_objects} 个对象 / {size_display}",
            metrics=[
                MetricItem(label="存储桶数量", value=f"{len(bucket_stats)} 个"),
                MetricItem(label="对象总数", value=f"{total_objects} 个"),
                MetricItem(label="已用容量", value=size_display),
            ],
            chart_data=bucket_stats,
        )
    except Exception as e:
        return StorageComponent(name="MinIO 对象存储", type="minio", status="error",
                                latency_ms=0, summary=str(e), metrics=[])


async def _detail_elasticsearch() -> StorageComponent:
    from app.core.config import settings
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            health_resp, stats_resp = await asyncio.gather(
                client.get(f"{settings.ELASTICSEARCH_URL}/_cluster/health"),
                client.get(f"{settings.ELASTICSEARCH_URL}/_stats/store,docs"),
                return_exceptions=True,
            )
        latency = (time.monotonic() - t0) * 1000

        cluster_status = "unknown"
        node_count = 0
        if isinstance(health_resp, httpx.Response) and health_resp.status_code == 200:
            hd = health_resp.json()
            cluster_status = hd.get("status", "unknown")
            node_count = hd.get("number_of_nodes", 0)

        doc_count = 0
        store_mb = 0.0
        index_count = 0
        if isinstance(stats_resp, httpx.Response) and stats_resp.status_code == 200:
            sd = stats_resp.json()
            totals = sd.get("_all", {}).get("total", {})
            doc_count = totals.get("docs", {}).get("count", 0)
            store_mb = round(totals.get("store", {}).get("size_in_bytes", 0) / 1024 / 1024, 1)
            index_count = len(sd.get("indices", {}))

        ok = cluster_status != "red"
        return StorageComponent(
            name="Elasticsearch", type="elasticsearch",
            status="ok" if ok else "error",
            latency_ms=round(latency, 2),
            summary=f"集群 {cluster_status} / {node_count} 节点 / {index_count} 个索引 / {doc_count:,} 文档",
            metrics=[
                MetricItem(label="集群状态", value=cluster_status.upper()),
                MetricItem(label="节点数量", value=f"{node_count} 个"),
                MetricItem(label="索引数量", value=f"{index_count} 个"),
                MetricItem(label="文档总数", value=f"{doc_count:,} 条"),
                MetricItem(label="索引大小", value=f"{store_mb} MB"),
            ],
        )
    except Exception as e:
        return StorageComponent(name="Elasticsearch", type="elasticsearch", status="error",
                                latency_ms=0, summary=str(e), metrics=[])


async def _detail_rabbitmq() -> StorageComponent:
    from app.core.config import settings
    t0 = time.monotonic()
    try:
        mq_host = settings.RABBITMQ_URL.split("@")[-1].split(":")[0] if "@" in settings.RABBITMQ_URL else "localhost"
        async with httpx.AsyncClient(timeout=3.0) as client:
            overview_resp, queues_resp = await asyncio.gather(
                client.get(f"http://{mq_host}:15672/api/overview", auth=("guest", "guest")),
                client.get(f"http://{mq_host}:15672/api/queues", auth=("guest", "guest")),
                return_exceptions=True,
            )
        latency = (time.monotonic() - t0) * 1000

        queue_count = 0
        messages_ready = 0
        messages_total = 0
        publish_rate = 0.0
        deliver_rate = 0.0

        if isinstance(overview_resp, httpx.Response) and overview_resp.status_code == 200:
            od = overview_resp.json()
            qt = od.get("queue_totals", {})
            messages_ready = qt.get("messages_ready", 0)
            messages_total = qt.get("messages", 0)
            ms = od.get("message_stats", {})
            publish_rate = ms.get("publish_details", {}).get("rate", 0.0)
            deliver_rate = ms.get("deliver_get_details", {}).get("rate", 0.0)

        if isinstance(queues_resp, httpx.Response) and queues_resp.status_code == 200:
            queue_count = len(queues_resp.json())

        return StorageComponent(
            name="RabbitMQ", type="rabbitmq", status="ok",
            latency_ms=round(latency, 2),
            summary=f"{queue_count} 个队列 / 待消费 {messages_ready} 条 / 发布 {publish_rate:.1f}/s",
            metrics=[
                MetricItem(label="队列数量", value=f"{queue_count} 个"),
                MetricItem(label="待消费消息", value=f"{messages_ready} 条"),
                MetricItem(label="消息总积压", value=f"{messages_total} 条"),
                MetricItem(label="发布速率", value=f"{publish_rate:.1f} 条/s"),
                MetricItem(label="消费速率", value=f"{deliver_rate:.1f} 条/s"),
            ],
        )
    except Exception as e:
        return StorageComponent(name="RabbitMQ", type="rabbitmq", status="error",
                                latency_ms=0, summary=str(e), metrics=[])
