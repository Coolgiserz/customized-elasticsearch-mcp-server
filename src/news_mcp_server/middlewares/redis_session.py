import json
import uuid
from itsdangerous import TimestampSigner, BadSignature
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from redis import asyncio as aioredis


class RedisSessionMiddleware(BaseHTTPMiddleware):
    """
    TODO 基于 Redis 的服务端 Session 中间件。
    - session 使用 UUID 作为 key 存储在 Redis 中
    - cookie 存储签名后的 session_id
    """
    def __init__(self, app, secret_key: str, redis_url: str, cookie_name: str = "session", max_age: int = 14*24*60*60):
        super().__init__(app)
        if not secret_key:
            raise ValueError("SESSION_SECRET_KEY 未配置")
        self.signer = TimestampSigner(secret_key)
        self.redis_url = redis_url
        self.cookie_name = cookie_name
        self.max_age = max_age
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            self._redis = await aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # 获取或生成 session_id
        session_id = None
        cookie = request.cookies.get(self.cookie_name)
        if cookie:
            try:
                unsigned = self.signer.unsign(cookie, max_age=self.max_age)
                session_id = unsigned.decode()
            except BadSignature:
                session_id = None
        if not session_id:
            session_id = str(uuid.uuid4())

        # 取 Redis 中的数据
        redis = await self._get_redis()
        raw = await redis.get(f"session:{session_id}")
        try:
            session_data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            session_data = {}
        request.scope["session"] = session_data

        # 调用下游
        response: Response = await call_next(request)

        # 写回 Redis
        await redis.setex(f"session:{session_id}", self.max_age, json.dumps(request.scope.get('session', {})))

        # 设置 cookie
        signed = self.signer.sign(session_id.encode()).decode()
        response.set_cookie(
            self.cookie_name,
            signed,
            max_age=self.max_age,
            httponly=True,
            samesite="lax"
        )
        return response 