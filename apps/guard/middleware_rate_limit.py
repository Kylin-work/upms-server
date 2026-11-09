from typing import ClassVar

from django.core.cache import cache
from django.http import JsonResponse


class RateLimitMiddleware:
    """IP 限流中间件，防止接口被恶意刷量."""

    # 定义限流规则：路径前缀 -> (最大请求次数, 时间窗口秒数)
    RULES: ClassVar = {
        "/api/v1/auth/login": (5, 60),  # 登录接口：1 分钟最多 5 次
        "/api/v1/auth/refresh": (10, 60),  # 刷新 Token：1 分钟最多 10 次
        "/api/v1/auth/change-password": (5, 60),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 获取客户端 IP
        ip = self._get_client_ip(request)

        # 检查是否命中了限流规则
        for path_prefix, (limit, window) in self.RULES.items():
            if request.path.startswith(path_prefix):
                if self._is_rate_limited(ip, path_prefix, limit, window):
                    return JsonResponse(
                        {
                            "code": 429,
                            "data": None,
                            "message": "请求过于频繁，请稍后再试",
                            "trace_id": getattr(request, "trace_id", ""),
                        },
                        status=429,
                    )
                break

        return self.get_response(request)

    def _get_client_ip(self, request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

    def _is_rate_limited(self, ip: str, path: str, limit: int, window: int) -> bool:
        key = f"rate_limit:{ip}:{path}"

        # 如果 key 不存在，初始化并设置过期时间
        if cache.add(key, 1, window):
            return False

        try:
            # 原子自增
            current_count = cache.incr(key)
            return current_count > limit
        except ValueError:
            # 极端情况下 key 过期了，重新初始化
            cache.set(key, 1, window)
            return False
