from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from ..utils.logger import logger

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        method = None
        params = None
        # 尝试解析 JSON-RPC 请求体中的方法名和参数
        if request.method.upper() == "POST":
            try:
                body = await request.json()
                method = body.get("method")
                params = body.get("params")
            except Exception:
                pass
        # 获取客户端 IP
        client_ip = None
        if request.client:
            client_ip = request.client.host
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        # 审计记录：工具名、参数、客户端IP、状态码、耗时(ms)
        logger.info(
            "mcp_tool_audit",
            method=method,
            params=params,
            client_ip=client_ip,
            status_code=response.status_code,
            duration_ms=int(duration * 1000)
        )
        return response
