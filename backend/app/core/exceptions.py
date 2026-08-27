"""全局异常与统一错误码。"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class BizError(HTTPException):
    """业务异常，携带统一错误码。"""

    def __init__(self, status_code: int, code: int, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message


async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    """业务异常统一返回格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """标准 HTTP 异常统一返回格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求参数校验异常统一返回格式。"""
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "请求参数校验失败", "data": exc.errors()},
    )
