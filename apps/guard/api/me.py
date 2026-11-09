from ninja import Router, Schema
from pydantic import Field

from apps.authz.services.snapshot import load_permission_snapshot
from apps.guard.services.perm import perm

router = Router(tags=["me"])


class UserBrief(Schema):
    id: int = Field(..., description="用户ID")
    name: str = Field(..., description="真实姓名")
    realm: str | None = Field(None, description="所属域(HQ/DIRECT/FRANCHISE),超管为NULL")
    org_id: int | None = Field(None, description="所属组织ID,超管为NULL")


class MenuNode(Schema):
    code: str = Field(..., description="菜单资源码")
    name: str = Field(..., description="菜单名称")
    icon: str | None = Field(None, description="图标标识")
    path: str | None = Field(None, description="前端路由路径")
    children: list["MenuNode"] = Field(default_factory=list, description="子菜单列表")


class PermissionsResponse(Schema):
    perm_version: int = Field(..., description="权限版本号")
    user: UserBrief = Field(..., description="当前用户摘要信息")
    menus: list[MenuNode] = Field(default_factory=list, description="已裁剪的菜单树")
    buttons: list[str] = Field(default_factory=list, description="当前用户可见的按钮编码列表")
    apis: list[str] = Field(default_factory=list, description="当前用户可调用的API资源码列表")
    data_scopes: dict = Field(..., description="数据范围配置,键为资源码或通配符*")
    column_masks: dict = Field(..., description="列级掩码配置,键为字段名")
    etag: str = Field(..., description="响应校验标识,用于条件请求")


class MenusResponse(Schema):
    perm_version: int = Field(..., description="权限版本号")
    menus: list[MenuNode] = Field(default_factory=list, description="已裁剪的菜单树")
    etag: str = Field(..., description="响应校验标识,用于条件请求")


class ButtonsResponse(Schema):
    perm_version: int = Field(..., description="权限版本号")
    buttons: list[str] = Field(default_factory=list, description="当前用户可见的按钮编码列表")
    etag: str = Field(..., description="响应校验标识,用于条件请求")


class DataScopesResponse(Schema):
    perm_version: int = Field(..., description="权限版本号")
    data_scopes: dict = Field(..., description="数据范围配置,键为资源码或通配符*")
    etag: str = Field(..., description="响应校验标识,用于条件请求")


@router.get(
    "/me/permissions",
    response=PermissionsResponse,
    auth=perm("me.perm.view"),
    summary="获取当前用户权限",
)
def get_my_permissions(request):
    """
    返回完整的权限快照。

    包含当前用户的菜单树、按钮编码、接口资源码以及数据范围。
    """
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "user": {
            "id": user.id,
            "name": user.real_name,
            "realm": user.realm,
            "org_id": user.org_id,
        },
        "menus": snapshot["menu_tree"],
        "buttons": snapshot["button_codes"],
        "apis": snapshot["api_codes"],
        "data_scopes": snapshot["data_scopes"],
        "column_masks": snapshot["column_masks"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }


@router.get(
    "/me/menus",
    response=MenusResponse,
    auth=perm("me.perm.view"),
    summary="获取当前用户菜单",
)
def get_my_menus(request):
    """
    返回当前用户可见的菜单树。
    """
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "menus": snapshot["menu_tree"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }


@router.get(
    "/me/buttons",
    response=ButtonsResponse,
    auth=perm("me.perm.view"),
    summary="获取当前用户按钮",
)
def get_my_buttons(request):
    """
    返回当前用户可见的按钮编码扁平列表。
    """
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "buttons": snapshot["button_codes"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }


@router.get(
    "/me/data-scopes",
    response=DataScopesResponse,
    auth=perm("me.perm.view"),
    summary="获取当前用户数据范围",
)
def get_my_data_scopes(request):
    """
    返回当前用户的数据范围字典。
    """
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "data_scopes": snapshot["data_scopes"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }
