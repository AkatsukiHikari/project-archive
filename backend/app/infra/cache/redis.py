from typing import Any, Optional
import json
import redis.asyncio as redis
from app.core.config import settings

class RedisService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True  # Important: Returns str instead of bytes
        )

    async def set(self, key: str, value: Any, expire: int = None):
        """Standard Set"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis.set(key, value, ex=expire)

    async def get(self, key: str) -> Optional[str]:
        """Standard Get"""
        return await self.redis.get(key)
    
    async def get_json(self, key: str) -> Optional[Any]:
        """Get and parse JSON"""
        val = await self.redis.get(key)
        if val:
            return json.loads(val)
        return None

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def get_and_delete(self, key: str) -> Optional[str]:
        """Get value and immediately delete the key (one-time use pattern)"""
        val = await self.redis.get(key)
        if val is not None:
            await self.redis.delete(key)
        return val

    async def get_json_and_delete(self, key: str) -> Optional[Any]:
        """Get JSON value and immediately delete the key (one-time use pattern)"""
        val = await self.redis.get(key)
        if val is not None:
            await self.redis.delete(key)
            return json.loads(val)
        return None

    async def close(self):
        await self.redis.close()

redis_service = RedisService()
