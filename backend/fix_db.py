import asyncio
from sqlalchemy import text
from app.infra.db.session import async_engine

async def main():
    async with async_engine.begin() as conn:
        await conn.execute(text("ALTER TABLE iam_user ADD COLUMN IF NOT EXISTS avatar VARCHAR(500);"))
        await conn.execute(text("ALTER TABLE iam_user ADD COLUMN IF NOT EXISTS phone VARCHAR(20);"))
        await conn.execute(text("ALTER TABLE iam_user ADD COLUMN IF NOT EXISTS job_title VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE iam_user ADD COLUMN IF NOT EXISTS location VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE iam_user ADD COLUMN IF NOT EXISTS bio VARCHAR(500);"))
        await conn.execute(text("ALTER TABLE iam_user ADD COLUMN IF NOT EXISTS last_login_time TIMESTAMP WITH TIME ZONE;"))
        print("Columns added successfully.")

if __name__ == "__main__":
    asyncio.run(main())
