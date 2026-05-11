"""One-shot script: update field_schema for all builtin archive categories."""
import asyncio
import json
import sys
import uuid

sys.path.insert(0, ".")

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.scripts.seed_archive_categories import BUILTIN_CATEGORIES


async def main() -> None:
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            text("SELECT code, name FROM repo_archive_category WHERE is_deleted = false")
        )
        existing = {row.code: row.name for row in result.fetchall()}
        print(f"Existing categories ({len(existing)}): {sorted(existing.keys())}")

        updated = 0
        inserted = 0

        for cat in BUILTIN_CATEGORIES:
            code = cat["code"]
            schema_json = json.dumps(cat["field_schema"], ensure_ascii=False)

            if code in existing:
                # Use cast() via SQLAlchemy to avoid asyncpg :: syntax conflict
                await session.execute(
                    text(
                        "UPDATE repo_archive_category "
                        "SET field_schema = cast(:schema as jsonb) "
                        "WHERE code = :code AND is_deleted = false"
                    ),
                    {"code": code, "schema": schema_json},
                )
                fields = cat["field_schema"]
                inherited = sum(1 for f in fields if f.get("inherited"))
                specific = len(fields) - inherited
                print(
                    f"  UPDATED {code:8s}: {len(fields):2d} fields "
                    f"({inherited} inh + {specific} spec)"
                )
                updated += 1
            else:
                await session.execute(
                    text(
                        "INSERT INTO repo_archive_category "
                        "(id, code, name, parent_id, sort_order, field_schema, is_builtin, is_deleted, create_time, update_time) "
                        "VALUES (:id, :code, :name, NULL, :sort_order, cast(:schema as jsonb), true, false, now(), now())"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "code": code,
                        "name": cat["name"],
                        "sort_order": cat.get("sort_order", 99),
                        "schema": schema_json,
                    },
                )
                print(f"  INSERTED {code}: {cat['name']}")
                inserted += 1

        await session.commit()
        print(f"\nDone: {updated} updated, {inserted} inserted")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
