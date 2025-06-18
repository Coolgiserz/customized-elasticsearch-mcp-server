# @Author: Zhu Guowei
# @Date: 2025/6/17
# @Function:
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from structlog import get_logger
logger = get_logger(__name__)
import os

ALLOW_HOSTS = ["172.20.80.1", "127.0.0.1"]
class SimpleAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key_env="API_KEY"):
        super().__init__(app)
        self.api_key = os.getenv(api_key_env)
        logger.info(f"api key: {self.api_key}")

    async def dispatch(self, request: Request, call_next):
        # 如果未配置 API_KEY，且允许跳过，则直接放行（便于开发环境）

        host = request.headers.get("HOST")
        logger.info(f"host: {host}, {request.headers}")
        for h in ALLOW_HOSTS:
            if h in host:
                return await call_next(request)
        if not self.api_key:
            logger.info(f"request.url: {request.url}")
            return await call_next(request)

        # 获取 Authorization头
        auth_header = request.headers.get("authorization")
        logger.info(f"url: {request.url}, query_params: {request.query_params}")
        logger.info(f"auth-header: {auth_header}")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse({"detail": "Bearer Token Not Provided"}, status_code=401)

        token = auth_header[7:].strip()
        if token != self.api_key:
            return JSONResponse({"detail": "Invalid Token"}, status_code=403)

        # 认证通过，继续处理请求
        return await call_next(request)