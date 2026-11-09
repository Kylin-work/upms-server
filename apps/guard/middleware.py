import json

from django.utils.deprecation import MiddlewareMixin


class UnifiedResponseMiddleware(MiddlewareMixin):
    """全局统一响应包装中间件."""

    def process_response(self, request, response):
        # 包含 application/json 头就处理
        content_type = response.get("Content-Type", "")
        if "application/json" in content_type:
            # 如果是 Ninja 的默认 404，不做处理
            if response.status_code == 404 and not response.content:
                return response

            try:
                data = json.loads(response.content)

                # 如果返回值已经是带有 code/data/message 的格式，直接跳过
                if isinstance(data, dict) and "code" in data and "message" in data:
                    return response

                # 否则进行包装
                wrapped_data = {
                    "code": 0 if response.status_code < 400 else response.status_code,
                    "data": data if response.status_code < 400 else None,
                    "message": "success" if response.status_code < 400 else "error",
                }

                response.content = json.dumps(wrapped_data, ensure_ascii=False)
                return response
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        return response
