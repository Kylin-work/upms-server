class GuardError(Exception):
    """guard 域基础异常，携带 HTTP 状态码与错误码。"""

    status_code = 400
    default_code = "GUARD_ERROR"

    def __init__(self, code: str | None = None, detail: str | None = None):
        self.code = code or self.default_code
        self.detail = detail or self.code
        super().__init__(self.detail)


class Unauthorized(GuardError):
    status_code = 401
    default_code = "UNAUTHORIZED"


class Forbidden(GuardError):
    status_code = 403
    default_code = "FORBIDDEN"
