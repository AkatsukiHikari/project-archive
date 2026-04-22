from typing import Any, Optional
import json
import redis.asyncio as redis
from app.core.config import settings


class RedisService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )

    async def set(self, key: str, value: Any, expire: int = None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis.set(key, value, ex=expire)

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def get_json(self, key: str) -> Optional[Any]:
        val = await self.redis.get(key)
        if val:
            return json.loads(val)
        return None

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def get_and_delete(self, key: str) -> Optional[str]:
        val = await self.redis.get(key)
        if val is not None:
            await self.redis.delete(key)
        return val

    async def get_json_and_delete(self, key: str) -> Optional[Any]:
        val = await self.redis.get(key)
        if val is not None:
            await self.redis.delete(key)
            return json.loads(val)
        return None

    async def publish(self, channel: str, message: str) -> int:
        """发布消息到 Redis pub/sub 频道，返回接收者数量。"""
        return await self.redis.publish(channel, message)

    def pubsub(self) -> redis.client.PubSub:
        """返回一个 pub/sub 订阅对象（供 WebSocket 进度推送使用）。"""
        return self.redis.pubsub()

    async def close(self):
        await self.redis.aclose()


redis_service = RedisService()


async def get_redis() -> RedisService:
    """FastAPI 依赖 / Celery 任务内均可直接调用。"""
    return redis_service
