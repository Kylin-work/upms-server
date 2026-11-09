from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.authz.services.resource import (
    ResourceServiceError,
    create_resource,
    disable_resource,
    get_resource_detail,
    update_resource,
)
from apps.guard.services.perm import perm

router = Router(tags=["authz"])


class ResourceOut(Schema):
    id: int = Field(..., description="资源ID")
    resource_code: str = Field(..., description="资源编码")
    resource_name: str = Field(..., description="资源名称")
    res_type: str = Field(..., description="资源类型: MENU/API/BUTTON")
    op_type: str = Field(..., description="操作类型: QUERY/WRITE/ADMIN")
    realm_scope: str = Field(..., description="适用范围: ALL/DIRECT/FRANCHISE")
    http_method: str | None = Field(None, description="HTTP 方法(仅API)")
    api_pattern: str | None = Field(None, description="API 路径模式(仅API)")
    is_public: bool = Field(..., description="是否公开(无需功能鉴权)")
    status: int = Field(..., description="状态: 1启用, 0停用")


class ResourceCreateIn(Schema):
    resource_code: str = Field(..., description="资源编码,全局唯一")
    resource_name: str = Field(..., description="资源名称")
    res_type: str = Field(..., description="资源类型")
    op_type: str = Field(..., description="操作类型")
    realm_scope: str = Field("ALL", description="适用范围")
    http_method: str | None = Field(None, description="HTTP 方法")
    api_pattern: str | None = Field(None, description="API 路径模式")
    menu_path: str | None = Field(None, description="菜单路由")
    menu_icon: str | None = Field(None, description="菜单图标")
    is_public: bool = Field(False, description="是否公开")
    parent_code: str | None = Field(None, description="父级资源编码")


class ResourceUpdateIn(Schema):
    resource_name: str | None = Field(None, description="资源名称")
    is_public: bool | None = Field(None, description="是否公开")
    menu_path: str | None = Field(None, description="菜单路由")
    menu_icon: str | None = Field(None, description="菜单图标")


@router.post("/authz/resources", response=ResourceOut, auth=perm("authz.resource.create"), summary="创建资源")
def create_resource_api(request, payload: ResourceCreateIn):
    """创建单个资源."""
    try:
        res = create_resource(
            resource_code=payload.resource_code,
            resource_name=payload.resource_name,
            res_type=payload.res_type,
            op_type=payload.op_type,
            realm_scope=payload.realm_scope,
            http_method=payload.http_method,
            api_pattern=payload.api_pattern,
            menu_path=payload.menu_path,
            menu_icon=payload.menu_icon,
            is_public=payload.is_public,
            parent_code=payload.parent_code,
        )
    except ResourceServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return res


@router.get("/authz/resources/{resource_id}", response=ResourceOut, auth=perm("authz.resource.view"), summary="获取资源详情")
def get_resource_api(request, resource_id: int):
    """根据 ID 查询资源详情."""
    try:
        res = get_resource_detail(resource_id)
    except ResourceServiceError as exc:
        raise HttpError(404, exc.code) from exc
    return res


@router.put("/authz/resources/{resource_id}", response=ResourceOut, auth=perm("authz.resource.update"), summary="更新资源")
def update_resource_api(request, resource_id: int, payload: ResourceUpdateIn):
    """更新资源基础信息."""
    try:
        res = update_resource(
            resource_id=resource_id,
            resource_name=payload.resource_name,
            is_public=payload.is_public,
            menu_path=payload.menu_path,
            menu_icon=payload.menu_icon,
        )
    except ResourceServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return res


@router.delete("/authz/resources/{resource_id}", auth=perm("authz.resource.disable"), summary="停用资源")
def disable_resource_api(request, resource_id: int):
    """停用指定资源(软删)."""
    try:
        disable_resource(resource_id=resource_id)
    except ResourceServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {"success": True}
