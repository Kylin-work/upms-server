from ninja.errors import HttpError, ValidationError
from ninja.responses import Response

from apps.guard.services.exceptions import GuardError


def error_handler(request, exc):
    """全局异常拦截器，把各种异常统一成 JSON 格式."""
    # 获取 trace_id
    trace_id = getattr(request, "trace_id", "")

    if isinstance(exc, GuardError):
        status = exc.status_code
        code = 1
        message = exc.code
    elif isinstance(exc, ValidationError):
        status = 422
        code = 422
        message = "参数校验失败"
        return Response(
            {
                "code": code,
                "data": exc.errors,
                "message": message,
                "trace_id": trace_id,
            },
            status=status,
        )
    elif isinstance(exc, HttpError):
        status = exc.status_code
        code = status
        message = str(exc.message)
    else:
        status = 500
        code = 500
        message = "服务器内部错误"

    return Response(
        {"code": code, "data": None, "message": message, "trace_id": trace_id},
        status=status,
    )
