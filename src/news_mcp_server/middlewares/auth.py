from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status
from structlog import get_logger
logger = get_logger(__name__)
import os
from typing import Optional
import ipaddress

ALLOW_HOSTS = ["172.20.80.1", "127.0.0.1"]

# 提取获取客户端真实 IP 的函数
def get_client_ip(request: Request) -> str:
    headers = request.headers
    x_forwarded_for = headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    return request.client.host

# 提取 IP 白名单判断函数
def is_ip_allowed(client_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    # 私有网络或回环地址自动放行
    if ip.is_private or ip.is_loopback:
        return True
    # 额外白名单
    return client_ip in ALLOW_HOSTS

# 提取解析 Bearer Token 的函数
def get_bearer_token(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    return auth_header[7:].strip()

# 提取设置认证通过标识函数
def mark_session_authenticated(request: Request) -> None:
    # 如果启用了 SessionMiddleware 或 RedisSessionMiddleware，scope['session'] 应该是 dict
    session = request.scope.get("session")
    if isinstance(session, dict):
        session["is_authenticated"] = True

class SimpleAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key_env="API_KEY"):
        super().__init__(app)
        self.api_key = os.getenv(api_key_env)
        if not self.api_key:
            raise RuntimeError("API_KEY must be set for SimpleAuthMiddleware")
        logger.info("SimpleAuthMiddleware initialized")

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization")
        client_ip = get_client_ip(request)
        if is_ip_allowed(client_ip):
            mark_session_authenticated(request)
            return await call_next(request)
        logger.info("simple-auth", client_ip=client_ip, header=auth_header)

        token = get_bearer_token(auth_header)
        if token is None:
            logger.warning("simple-auth", client_ip=client_ip, detail="Bearer Token Not Provided", header=auth_header)
            return JSONResponse({"detail": "Bearer Token Not Provided"}, status_code=status.HTTP_401_UNAUTHORIZED)

        if token != self.api_key:
            logger.warning("simple-auth", client_ip=client_ip, detail="Invalid Token", token=token, header=auth_header)
            return JSONResponse({"detail": "Invalid Token"}, status_code=status.HTTP_403_FORBIDDEN)

        # 认证通过，设置 session 标识并继续处理
        mark_session_authenticated(request)
        return await call_next(request)