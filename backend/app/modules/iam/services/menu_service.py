from typing import List, Optional
from fastapi import HTTPException
from app.modules.iam import schemas
from app.modules.iam.repositories.menu_repository import MenuRepository
from app.modules.iam.models import Menu
import uuid

class MenuService:
    def __init__(self, menu_repo: MenuRepository):
        self.menu_repo = menu_repo

    async def get_menu(self, menu_id: uuid.UUID) -> Menu:
        menu = await self.menu_repo.get_by_id(menu_id)
        if not menu:
            raise HTTPException(status_code=404, detail="菜单/权限不存在")
        return menu

    async def get_menu_tree(self) -> List[schemas.MenuTree]:
        menus = await self.menu_repo.get_all()

        # 逐个将 ORM 对象手动映射为 MenuTree，避免 Pydantic 验证 SQLAlchemy
        # InstrumentedList（children 关系属性）时报 validation error
        menu_dict: dict[uuid.UUID, schemas.MenuTree] = {}
        for m in menus:
            menu_dict[m.id] = schemas.MenuTree(
                id=m.id,
                parent_id=m.parent_id,
                code=m.code,
                name=m.name,
                type=m.type,
                path=m.path,
                icon=m.icon,
                sort_order=m.sort_order,
                is_visible=m.is_visible,
                is_system=getattr(m, "is_system", False),
                create_time=m.create_time,
                update_time=m.update_time,
                children=[],
            )

        root_nodes: List[schemas.MenuTree] = []
        for m in menus:
            node = menu_dict[m.id]
            if m.parent_id and m.parent_id in menu_dict:
                menu_dict[m.parent_id].children.append(node)
            else:
                root_nodes.append(node)

        def sort_tree(nodes: List[schemas.MenuTree]) -> None:
            nodes.sort(key=lambda x: x.sort_order)
            for node in nodes:
                sort_tree(node.children)

        sort_tree(root_nodes)
        return root_nodes

    async def create_menu(self, menu_in: schemas.MenuCreate) -> Menu:
        existing = await self.menu_repo.get_by_code(menu_in.code)
        if existing:
            raise HTTPException(status_code=400, detail="菜单编码已存在")
            
        if menu_in.parent_id:
            await self.get_menu(menu_in.parent_id)
            
        return await self.menu_repo.create(menu_in)

    async def update_menu(self, menu_id: uuid.UUID, menu_in: schemas.MenuUpdate) -> Menu:
        menu = await self.get_menu(menu_id)
        
        if menu_in.code and menu_in.code != menu.code:
            existing = await self.menu_repo.get_by_code(menu_in.code)
            if existing:
                raise HTTPException(status_code=400, detail="菜单编码已存在")
                
        if menu_in.parent_id:
            await self.get_menu(menu_in.parent_id)
            if menu_in.parent_id == menu.id:
                raise HTTPException(status_code=400, detail="不能将自己设为父节点")
                
        return await self.menu_repo.update(menu, menu_in)

    async def delete_menu(self, menu_id: uuid.UUID) -> bool:
        menu = await self.get_menu(menu_id)
        if getattr(menu, "is_system", False):
            raise HTTPException(status_code=400, detail="系统内置菜单不可删除")
        return await self.menu_repo.delete(menu.id)
