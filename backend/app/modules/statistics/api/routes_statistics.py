"""档案统计 API。

挂载前缀： /statistics

综合统计  GET /overview?fonds_id=
大屏驾驶舱 GET /cockpit
年度报表  GET /annual-reports, GET /annual-reports/{year},
          POST /annual-reports/{year}/generate | /finalize | /reopen,
          PUT  /annual-reports/{year}
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.statistics.services.annual_service import AnnualReportService
from app.modules.statistics.services.overview_service import OverviewService

router = APIRouter(prefix="/statistics", tags=["档案统计"])


# ── 综合统计 / 驾驶舱 ─────────────────────────────────────────────────────────


@router.get("/overview", response_model=ResponseModel[dict])
async def get_overview(
    fonds_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OverviewService(db)
    data = await svc.overview(current_user.tenant_id, fonds_id)
    return success(data)


@router.get("/cockpit", response_model=ResponseModel[dict])
async def get_cockpit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OverviewService(db)
    data = await svc.cockpit(current_user.tenant_id)
    return success(data)


# ── 年度报表 ──────────────────────────────────────────────────────────────────


def _report_payload(report, definitions: bool = True) -> dict:
    data = {
        "year": report.year,
        "status": report.status,
        "auto_data": report.auto_data or {},
        "manual_data": report.manual_data or {},
        "generated_at": (
            report.generated_at.isoformat() if report.generated_at else None
        ),
        "finalized_at": (
            report.finalized_at.isoformat() if report.finalized_at else None
        ),
    }
    if definitions:
        data["definitions"] = AnnualReportService.definitions()
    return data


@router.get("/annual-reports", response_model=ResponseModel[list[dict]])
async def list_annual_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AnnualReportService(db)
    reports = await svc.list_reports(current_user.tenant_id)
    return success([_report_payload(r, definitions=False) for r in reports])


@router.get("/annual-reports/{year}", response_model=ResponseModel[dict])
async def get_annual_report(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AnnualReportService(db)
    report = await svc.get_report(year, current_user.tenant_id)
    if report is None:
        # 未生成：返回空报告 + 指标定义，前端引导一键生成
        return success(
            {
                "year": year,
                "status": "none",
                "auto_data": {},
                "manual_data": {},
                "generated_at": None,
                "finalized_at": None,
                "definitions": AnnualReportService.definitions(),
            }
        )
    return success(_report_payload(report))


@router.post("/annual-reports/{year}/generate", response_model=ResponseModel[dict])
async def generate_annual_report(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AnnualReportService(db)
    report = await svc.generate(year, current_user.id, current_user.tenant_id)
    await db.commit()
    return success(_report_payload(report))


@router.put("/annual-reports/{year}", response_model=ResponseModel[dict])
async def save_annual_report(
    year: int,
    manual_data: dict = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AnnualReportService(db)
    report = await svc.save_manual(year, manual_data, current_user.tenant_id)
    await db.commit()
    return success(_report_payload(report))


@router.post("/annual-reports/{year}/finalize", response_model=ResponseModel[dict])
async def finalize_annual_report(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AnnualReportService(db)
    report = await svc.finalize(year, current_user.tenant_id)
    await db.commit()
    return success(_report_payload(report))


@router.post("/annual-reports/{year}/reopen", response_model=ResponseModel[dict])
async def reopen_annual_report(
    year: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AnnualReportService(db)
    report = await svc.reopen(year, current_user.tenant_id)
    await db.commit()
    return success(_report_payload(report))
