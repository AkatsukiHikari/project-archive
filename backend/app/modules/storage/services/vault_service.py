"""库房管理：库房 CRUD + 架位网格自动生成 + 保管台账聚合。"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.repository.models.archive import Archive
from app.modules.storage.models import StorageInout, StorageShelf, StorageVault
from app.modules.storage.schemas.vault import VaultCreate, VaultUpdate


class VaultService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 占用率实时统计（按档案 shelf_id 关联，不再用手填的 used 列）──────────────

    async def _vault_used_map(
        self, tenant_id: Optional[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """各库房实放档案件数 = 该库房所有架位上关联的档案数。"""
        stmt = (
            select(StorageShelf.vault_id, func.count(Archive.id))
            .join(Archive, Archive.shelf_id == StorageShelf.id)
            .where(
                StorageShelf.is_deleted.is_(False),
                Archive.is_deleted.is_(False),
                Archive.status != "destroyed",
            )
            .group_by(StorageShelf.vault_id)
        )
        if tenant_id:
            stmt = stmt.where(StorageShelf.tenant_id == tenant_id)
        return {r[0]: r[1] for r in (await self.db.execute(stmt)).all()}

    async def _shelf_used_map(self, vault_id: uuid.UUID) -> dict[uuid.UUID, int]:
        """某库房各架位实放档案件数。"""
        stmt = (
            select(Archive.shelf_id, func.count())
            .join(StorageShelf, Archive.shelf_id == StorageShelf.id)
            .where(
                StorageShelf.vault_id == vault_id,
                Archive.is_deleted.is_(False),
                Archive.status != "destroyed",
            )
            .group_by(Archive.shelf_id)
        )
        return {r[0]: r[1] for r in (await self.db.execute(stmt)).all()}

    # ── 库房 ──────────────────────────────────────────────────────────────────

    async def list_vaults(self, tenant_id: Optional[uuid.UUID]) -> list[dict]:
        stmt = select(StorageVault).where(StorageVault.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(StorageVault.tenant_id == tenant_id)
        vaults = (
            (await self.db.execute(stmt.order_by(StorageVault.code))).scalars().all()
        )
        used_map = await self._vault_used_map(tenant_id)
        return [self._vault_dict(v, used_map.get(v.id, 0)) for v in vaults]

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
        shelf_used = await self._shelf_used_map(vault.id)
        vault_used = sum(shelf_used.values())
        data = self._vault_dict(vault, vault_used)
        data["shelves"] = [
            {
                "id": s.id,
                "code": s.code,
                "row_index": s.row_index,
                "col_index": s.col_index,
                "capacity": s.capacity,
                "used": shelf_used.get(s.id, 0),
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
    def _vault_dict(v: StorageVault, used: int) -> dict:
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
            "used": used,
            "temperature": v.temperature,
            "humidity": v.humidity,
            "status": v.status,
            "manager_id": v.manager_id,
            "notes": v.notes,
            "fill_rate": round(used / v.capacity * 100, 1) if v.capacity else 0.0,
        }

    # ── 架位管理 ──────────────────────────────────────────────────────────────

    async def shelf_detail(
        self, shelf_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        """架位详情：容量/已用 + 该架位上的档案清单。"""
        shelf = await self._require_shelf(shelf_id, tenant_id)
        rows = (
            (
                await self.db.execute(
                    select(Archive)
                    .where(
                        Archive.shelf_id == shelf_id,
                        Archive.is_deleted.is_(False),
                        Archive.status != "destroyed",
                    )
                    .order_by(Archive.DH.asc().nulls_last())
                )
            )
            .scalars()
            .all()
        )
        return {
            "id": shelf.id,
            "code": shelf.code,
            "capacity": shelf.capacity,
            "used": len(rows),
            "label": shelf.label,
            "archives": [
                {"id": a.id, "DH": a.DH, "TM": a.TM, "ND": a.ND, "QZH": a.QZH}
                for a in rows
            ],
        }

    async def update_shelf(
        self,
        shelf_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        capacity: Optional[int] = None,
        label: Optional[str] = None,
    ) -> StorageShelf:
        shelf = await self._require_shelf(shelf_id, tenant_id)
        if capacity is not None:
            shelf.capacity = capacity
        if label is not None:
            shelf.label = label
        await self.db.flush()
        return shelf

    async def assign_archives(
        self,
        shelf_id: uuid.UUID,
        archive_ids: list[uuid.UUID],
        tenant_id: Optional[uuid.UUID],
    ) -> int:
        """上架：把档案放到该架位。"""
        from sqlalchemy import update

        await self._require_shelf(shelf_id, tenant_id)
        result = await self.db.execute(
            update(Archive)
            .where(Archive.id.in_(archive_ids), Archive.is_deleted.is_(False))
            .values(shelf_id=shelf_id)
        )
        return result.rowcount or 0

    async def unassign_archives(
        self, archive_ids: list[uuid.UUID], tenant_id: Optional[uuid.UUID]
    ) -> int:
        """下架：清除档案的架位关联。"""
        from sqlalchemy import update

        result = await self.db.execute(
            update(Archive)
            .where(Archive.id.in_(archive_ids), Archive.is_deleted.is_(False))
            .values(shelf_id=None)
        )
        return result.rowcount or 0

    async def list_unshelved(
        self,
        tenant_id: Optional[uuid.UUID],
        keyword: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """待上架档案：正式库中尚未关联架位的档案，供上架挑选。"""
        stmt = select(Archive).where(
            Archive.is_deleted.is_(False),
            Archive.status != "destroyed",
            Archive.shelf_id.is_(None),
        )
        if tenant_id:
            stmt = stmt.where(Archive.tenant_id == tenant_id)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(Archive.TM.ilike(like) | Archive.DH.ilike(like))
        rows = (
            (
                await self.db.execute(
                    stmt.order_by(Archive.DH.asc().nulls_last()).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [
            {"id": a.id, "DH": a.DH, "TM": a.TM, "ND": a.ND, "QZH": a.QZH} for a in rows
        ]

    async def _require_shelf(
        self, shelf_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> StorageShelf:
        stmt = select(StorageShelf).where(
            StorageShelf.id == shelf_id, StorageShelf.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(StorageShelf.tenant_id == tenant_id)
        shelf = (await self.db.execute(stmt)).scalars().first()
        if not shelf:
            raise NotFoundException(
                code=ErrorCode.VAULT_NOT_FOUND, message="架位不存在"
            )
        return shelf

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
