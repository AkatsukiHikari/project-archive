import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.services.fonds_service import FondsService
from app.modules.repository.schemas.fonds import FondsCreate, FondsUpdate, FondsRead
from app.common.response import success, ResponseModel

router = APIRouter(prefix="/archive/fonds", tags=["全宗管理"])


@router.get("", response_model=ResponseModel[list[FondsRead]])
async def list_fonds(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = FondsService(db)
    items = await svc.list_all(tenant_id=current_user.tenant_id)
    return success([FondsRead.model_validate(i) for i in items])


@router.post("", response_model=ResponseModel[FondsRead])
async def create_fonds(
    data: FondsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = FondsService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(FondsRead.model_validate(item))


@router.put("/{fonds_id}", response_model=ResponseModel[FondsRead])
async def update_fonds(
    fonds_id: uuid.UUID,
    data: FondsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = FondsService(db)
    item = await svc.update(fonds_id, data)
    await db.commit()
    return success(FondsRead.model_validate(item))


@router.delete("/{fonds_id}", response_model=ResponseModel[None])
async def delete_fonds(
    fonds_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = FondsService(db)
    await svc.delete(fonds_id)
    await db.commit()
    return success()
