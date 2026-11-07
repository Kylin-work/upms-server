from django.http import HttpRequest

from apps.authz.services.snapshot import load_permission_snapshot
from apps.guard.services.auth import authenticate
from apps.guard.services.exceptions import Forbidden
from apps.guard.services.registry import get_resource


def authorize(request: HttpRequest, resource_code: str) -> None:
    user = request.user
    resource = get_resource(resource_code)
    if resource is None:
        raise Forbidden("RESOURCE_NOT_REGISTERED")

    snapshot = load_permission_snapshot(user)

    if resource_code not in snapshot["api_codes"]:
        raise Forbidden("NO_FUNCTION_PERM")

    request.ctx_data_scope = snapshot["data_scopes"].get(
        resource_code,
        snapshot["data_scopes"].get("*"),
    )


def perm(resource_code: str):
    """Ninja 依赖工厂:认证 + 功能鉴权 + 注入数据范围上下文."""

    def _dependency(request: HttpRequest):
        user = authenticate(request)
        authorize(request, resource_code)
        return user

    return _dependency
