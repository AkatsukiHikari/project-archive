from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.infra.db.session import get_db
from app.modules.preservation.services.preservation_service import PreservationService


def get_detection_service(db: AsyncSession = Depends(get_db)) -> PreservationService:
    return PreservationService()
