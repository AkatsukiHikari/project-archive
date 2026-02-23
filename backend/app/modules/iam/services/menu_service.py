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
        
        # Build tree
        menu_dict = {menu.id: schemas.MenuTree.model_validate(menu) for menu in menus}
        root_nodes = []
        
        for menu in menus:
            if menu.parent_id and menu.parent_id in menu_dict:
                menu_dict[menu.parent_id].children.append(menu_dict[menu.id])
            else:
                root_nodes.append(menu_dict[menu.id])
                
        # Sort children by sort_order
        def sort_tree(nodes: List[schemas.MenuTree]):
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
        return await self.menu_repo.delete(menu.id)
