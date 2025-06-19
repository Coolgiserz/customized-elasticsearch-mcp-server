import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status
from redis import asyncio as aioredis
from ..utils.logger import logger


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于 Redis 的简单 IP 限流中间件。
    每个 IP 在固定时间窗口内最多允许 max_requests 次请求。
    """
    def __init__(self, app, redis_url: str, max_requests: int, window_seconds: int):
        super().__init__(app)
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window = window_seconds
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            # 仅在首次调用时创建 Redis 连接
            self._redis = await aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # 获取客户端 IP
        client_host = request.client.host if request.client else "unknown"
        logger.debug("rate-limiter", host=client_host)
        # 计算当前时间窗口
        now = int(time.time())
        window_key = now // self.window
        key = f"ratelimit:{client_host}:{window_key}"
        redis = await self._get_redis()
        # 自增计数
        count = await redis.incr(key)
        if count == 1:
            # 设置过期时间为一个窗口长度
            await redis.expire(key, self.window)

        # 超出限流阈值，返回 429
        if count > self.max_requests:
            logger.info("rate-limiter", host=client_host, key=key)
            return JSONResponse(
                {"detail": "请求过多，请稍后重试"},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # 继续处理请求
        response = await call_next(request)
        return response 