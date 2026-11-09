import logging
import time
import uuid

logger = logging.getLogger("upms.request")


class TraceIDMiddleware:
    """请求追踪中间件，生成 Trace ID 并记录请求耗时日志."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 生成 trace_id（或者从上游 Nginx 获取透传的）
        trace_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.trace_id = trace_id

        start_time = time.time()

        response = self.get_response(request)

        cost_ms = int((time.time() - start_time) * 1000)
        # 把 trace_id 塞进响应头，方便前端排查问题
        response["X-Request-ID"] = trace_id

        # 忽略静态资源等无聊请求
        if request.path in ("/favicon.ico", "/api/v1/docs", "/api/v1/openapi.json"):
            return response

        # 优先从 authenticate 挂载的标记里取，取不到再兜底
        user_id = getattr(request, "authenticated_user_id", "anonymous")

        log_msg = (
            f"trace_id={trace_id} "
            f"method={request.method} "
            f"path={request.path} "
            f"status={response.status_code} "
            f"user_id={user_id} "
            f"cost_ms={cost_ms}ms"
        )

        if response.status_code >= 400:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return response
