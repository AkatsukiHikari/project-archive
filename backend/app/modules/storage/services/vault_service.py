"""库房管理：库房 CRUD + 架位网格自动生成 + 保管台账聚合。"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.storage.models import StorageInout, StorageShelf, StorageVault
from app.modules.storage.schemas.vault import VaultCreate, VaultUpdate


class VaultService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 库房 ──────────────────────────────────────────────────────────────────

    async def list_vaults(self, tenant_id: Optional[uuid.UUID]) -> list[dict]:
        stmt = select(StorageVault).where(StorageVault.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(StorageVault.tenant_id == tenant_id)
        vaults = (
            (await self.db.execute(stmt.order_by(StorageVault.code))).scalars().all()
        )
        return [self._vault_dict(v) for v in vaults]

    async def get_vault(
        self, vault_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        vault = await self._require(vault_id, tenant_id)
        shelves = (
            (
                await self.db.execute(
                    select(StorageShelf)
                    .where(
                        StorageShelf.vault_id == vault.id,
                        StorageShelf.is_deleted.is_(False),
                    )
                    .order_by(StorageShelf.row_index, StorageShelf.col_index)
                )
            )
            .scalars()
            .all()
        )
        data = self._vault_dict(vault)
        data["shelves"] = [
            {
                "id": s.id,
                "code": s.code,
                "row_index": s.row_index,
                "col_index": s.col_index,
                "capacity": s.capacity,
                "used": s.used,
                "label": s.label,
            }
            for s in shelves
        ]
        return data

    async def create_vault(
        self, body: VaultCreate, tenant_id: Optional[uuid.UUID]
    ) -> StorageVault:
        dup = (
            await self.db.execute(
                select(func.count())
                .select_from(StorageVault)
                .where(
                    StorageVault.code == body.code, StorageVault.is_deleted.is_(False)
                )
            )
        ).scalar_one()
        if dup:
            raise ValidationException(
                code=ErrorCode.VAULT_CODE_EXISTS, message=f"库房编号 {body.code} 已存在"
            )
        vault = StorageVault(**body.model_dump(), tenant_id=tenant_id)
        self.db.add(vault)
        await self.db.flush()
        await self._regen_shelves(vault)
        await self.db.flush()
        return vault

    async def update_vault(
        self, vault_id: uuid.UUID, body: VaultUpdate, tenant_id: Optional[uuid.UUID]
    ) -> StorageVault:
        vault = await self._require(vault_id, tenant_id)
        data = body.model_dump(exclude_unset=True)
        grid_changed = any(k in data for k in ("rows", "columns"))
        for field, value in data.items():
            setattr(vault, field, value)
        await self.db.flush()
        if grid_changed:
            await self._regen_shelves(vault)
            await self.db.flush()
        return vault

    async def delete_vault(
        self, vault_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        vault = await self._require(vault_id, tenant_id)
        vault.is_deleted = True

    async def _regen_shelves(self, vault: StorageVault) -> None:
        """按 rows×columns 重建架位网格；保留已有架位的占用数据。"""
        existing = {
            (s.row_index, s.col_index): s
            for s in (
                await self.db.execute(
                    select(StorageShelf).where(
                        StorageShelf.vault_id == vault.id,
                        StorageShelf.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        }
        per_shelf = max(1, vault.capacity // max(1, vault.rows * vault.columns))
        for r in range(vault.rows):
            for cidx in range(vault.columns):
                shelf = existing.pop((r, cidx), None)
                code = f"{chr(65 + r)}-{cidx + 1:02d}"
                if shelf:
                    shelf.capacity = per_shelf
                else:
                    self.db.add(
                        StorageShelf(
                            vault_id=vault.id,
                            code=code,
                            row_index=r,
                            col_index=cidx,
                            capacity=per_shelf,
                            used=0,
                            tenant_id=vault.tenant_id,
                        )
                    )
        # 网格缩小后多余的架位软删
        for leftover in existing.values():
            leftover.is_deleted = True

    async def _require(
        self, vault_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> StorageVault:
        stmt = select(StorageVault).where(
            StorageVault.id == vault_id, StorageVault.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(StorageVault.tenant_id == tenant_id)
        vault = (await self.db.execute(stmt)).scalars().first()
        if not vault:
            raise NotFoundException(
                code=ErrorCode.VAULT_NOT_FOUND, message="库房不存在"
            )
        return vault

    @staticmethod
    def _vault_dict(v: StorageVault) -> dict:
        return {
            "id": v.id,
            "code": v.code,
            "name": v.name,
            "location": v.location,
            "area_sqm": v.area_sqm,
            "rows": v.rows,
            "columns": v.columns,
            "layers": v.layers,
            "capacity": v.capacity,
            "used": v.used,
            "temperature": v.temperature,
            "humidity": v.humidity,
            "status": v.status,
            "manager_id": v.manager_id,
            "notes": v.notes,
            "fill_rate": round(v.used / v.capacity * 100, 1) if v.capacity else 0.0,
        }

    # ── 保管台账 ──────────────────────────────────────────────────────────────

    async def ledger(self, tenant_id: Optional[uuid.UUID]) -> dict:
        vaults = await self.list_vaults(tenant_id)
        total_cap = sum(v["capacity"] for v in vaults)
        total_used = sum(v["used"] for v in vaults)

        out_active = await self._count_inout(tenant_id, status="out")
        cnt_total = await self._count_inout(tenant_id)

        return {
            "summary": {
                "vault_count": len(vaults),
                "total_capacity": total_cap,
                "total_used": total_used,
                "fill_rate": (
                    round(total_used / total_cap * 100, 1) if total_cap else 0.0
                ),
                "out_active": out_active,
                "inout_total": cnt_total,
            },
            "vaults": vaults,
        }

    async def _count_inout(
        self, tenant_id: Optional[uuid.UUID], status: Optional[str] = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(StorageInout)
            .where(StorageInout.is_deleted.is_(False))
        )
        if tenant_id:
            stmt = stmt.where(StorageInout.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(StorageInout.status == status)
        return (await self.db.execute(stmt)).scalar_one() or 0
