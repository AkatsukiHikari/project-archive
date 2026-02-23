from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.iam.models import Menu
from app.modules.iam import schemas
import uuid

class MenuRepository(ABC):
    @abstractmethod
    async def get_by_id(self, menu_id: uuid.UUID) -> Optional[Menu]:
        pass

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[Menu]:
        pass

    @abstractmethod
    async def get_all(self) -> List[Menu]:
        pass

    @abstractmethod
    async def create(self, menu_in: schemas.MenuCreate) -> Menu:
        pass

    @abstractmethod
    async def update(self, menu: Menu, menu_in: schemas.MenuUpdate) -> Menu:
        pass

    @abstractmethod
    async def delete(self, menu_id: uuid.UUID) -> bool:
        pass


class SQLAlchemyMenuRepository(MenuRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, menu_id: uuid.UUID) -> Optional[Menu]:
        result = await self.db.execute(select(Menu).where(Menu.id == menu_id, Menu.is_deleted == False))
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[Menu]:
        result = await self.db.execute(select(Menu).where(Menu.code == code, Menu.is_deleted == False))
        return result.scalars().first()

    async def get_all(self) -> List[Menu]:
        result = await self.db.execute(
            select(Menu)
            .where(Menu.is_deleted == False)
            .order_by(Menu.sort_order)
        )
        return list(result.scalars().all())

    async def create(self, menu_in: schemas.MenuCreate) -> Menu:
        db_menu = Menu(
            parent_id=menu_in.parent_id,
            code=menu_in.code,
            name=menu_in.name,
            type=menu_in.type,
            path=menu_in.path,
            icon=menu_in.icon,
            sort_order=menu_in.sort_order,
            is_visible=menu_in.is_visible
        )
        self.db.add(db_menu)
        await self.db.commit()
        await self.db.refresh(db_menu)
        return db_menu

    async def update(self, menu: Menu, menu_in: schemas.MenuUpdate) -> Menu:
        update_data = menu_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(menu, field, value)
        await self.db.commit()
        await self.db.refresh(menu)
        return menu

    async def delete(self, menu_id: uuid.UUID) -> bool:
        menu = await self.get_by_id(menu_id)
        if menu:
            menu.is_deleted = True
            await self.db.commit()
            return True
        return False
