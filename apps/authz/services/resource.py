from django.db import transaction

from apps.authz.models import SysResource


class ResourceServiceError(Exception):
    """资源操作异常，携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


@transaction.atomic
def create_resource(
    *,
    resource_code: str,
    resource_name: str,
    res_type: str,
    op_type: str,
    realm_scope: str = "ALL",
    http_method: str | None = None,
    api_pattern: str | None = None,
    menu_path: str | None = None,
    menu_icon: str | None = None,
    is_public: bool = False,
    parent_code: str | None = None,
) -> SysResource:
    """创建资源."""
    if SysResource.objects.filter(resource_code=resource_code).exists():
        raise ResourceServiceError("RESOURCE_CODE_DUPLICATE")

    if res_type == "API" and (not http_method or not api_pattern):
        raise ResourceServiceError("API_REQUIRE_METHOD_AND_PATTERN")

    parent = None
    if parent_code:
        parent = SysResource.objects.filter(resource_code=parent_code, status=1).first()
        if not parent:
            raise ResourceServiceError("PARENT_NOT_FOUND")

    resource = SysResource.objects.create(
        resource_code=resource_code,
        resource_name=resource_name,
        res_type=res_type,
        op_type=op_type,
        realm_scope=realm_scope,
        http_method=http_method,
        api_pattern=api_pattern,
        menu_path=menu_path,
        menu_icon=menu_icon,
        parent=parent,
        is_public=is_public,
        status=1,
    )
    _invalidate_registry()
    return resource


@transaction.atomic
def update_resource(
    *,
    resource_id: int,
    resource_name: str | None = None,
    is_public: bool | None = None,
    menu_path: str | None = None,
    menu_icon: str | None = None,
) -> SysResource:
    """更新资源基础信息."""
    resource = SysResource.objects.filter(id=resource_id).first()
    if not resource:
        raise ResourceServiceError("RESOURCE_NOT_FOUND")

    update_fields = []
    if resource_name is not None:
        resource.resource_name = resource_name
        update_fields.append("resource_name")
    if is_public is not None:
        resource.is_public = is_public
        update_fields.append("is_public")
    if menu_path is not None:
        resource.menu_path = menu_path
        update_fields.append("menu_path")
    if menu_icon is not None:
        resource.menu_icon = menu_icon
        update_fields.append("menu_icon")

    if update_fields:
        resource.save(update_fields=update_fields)
    _invalidate_registry()
    return resource


@transaction.atomic
def disable_resource(*, resource_id: int) -> SysResource:
    """停用资源（软删）."""
    resource = SysResource.objects.filter(id=resource_id).first()
    if not resource:
        raise ResourceServiceError("RESOURCE_NOT_FOUND")
    if resource.status == 0:
        raise ResourceServiceError("RESOURCE_ALREADY_DISABLED")

    resource.status = 0
    resource.save(update_fields=["status"])
    _invalidate_registry()
    return resource


def get_resource_detail(resource_id: int) -> SysResource:
    """获取资源详情."""
    resource = SysResource.objects.filter(id=resource_id).first()
    if not resource:
        raise ResourceServiceError("RESOURCE_NOT_FOUND")
    return resource


def _invalidate_registry():
    from apps.guard.services.registry import invalidate_registry
    invalidate_registry()
