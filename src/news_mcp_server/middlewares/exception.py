# @Author: Zhu Guowei
# @Date: 2025/6/18
# @Function:
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status
from typing import Callable
import traceback

from ..utils.logger import logger

class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # 记录完整异常栈
            tb = traceback.format_exc()
            logger.error(f"Unhandled exception processing request {request.method} {request.url}: {exc}")
            # 返回统一格式的错误响应
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
