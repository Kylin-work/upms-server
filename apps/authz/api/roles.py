from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.authz.services.role import (
    RoleServiceError,
    create_role,
    disable_role,
    get_role_detail,
    update_role,
)
from apps.guard.services.perm import perm

router = Router(tags=["authz"])


class RoleOut(Schema):
    id: int = Field(..., description="角色ID")
    role_code: str = Field(..., description="角色编码")
    role_name: str = Field(..., description="角色名称")
    realm: str = Field(..., description="所属域: HQ/DIRECT/FRANCHISE")
    role_type: str = Field(..., description="角色类型")
    org_id: int | None = Field(None, description="绑定的部门ID(仅FUNC_BIZ有)")
    data_scope_type: str = Field(..., description="数据范围类型")
    assignable_level: str = Field(..., description="可授予层级")
    is_builtin: bool = Field(..., description="是否内置角色")
    status: int = Field(..., description="状态: 1启用, 0停用")
    remark: str | None = Field(None, description="备注")


class RoleCreateIn(Schema):
    role_code: str = Field(..., description="角色编码,全局唯一")
    role_name: str = Field(..., description="角色名称")
    realm: str = Field(..., description="所属域")
    role_type: str = Field(..., description="角色类型")
    data_scope_type: str = Field(..., description="数据范围类型")
    assignable_level: str = Field(..., description="可授予层级")
    org_code: str | None = Field(None, description="绑定的部门编码")
    remark: str | None = Field(None, description="备注")


class RoleUpdateIn(Schema):
    role_name: str | None = Field(None, description="角色名称")
    remark: str | None = Field(None, description="备注")


@router.post(
    "/authz/roles", response=RoleOut, auth=perm("authz.role.create"), summary="创建角色"
)
def create_role_api(request, payload: RoleCreateIn):
    """创建单个角色."""
    try:
        role = create_role(
            role_code=payload.role_code,
            role_name=payload.role_name,
            realm=payload.realm,
            role_type=payload.role_type,
            data_scope_type=payload.data_scope_type,
            assignable_level=payload.assignable_level,
            org_code=payload.org_code,
            remark=payload.remark,
        )
    except RoleServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return role


@router.get(
    "/authz/roles/{role_id}",
    response=RoleOut,
    auth=perm("authz.role.view"),
    summary="获取角色详情",
)
def get_role_api(request, role_id: int):
    """根据 ID 查询角色详情."""
    try:
        role = get_role_detail(role_id, request.ctx_data_scope)
    except RoleServiceError as exc:
        raise HttpError(404, exc.code) from exc
    return role


@router.put(
    "/authz/roles/{role_id}",
    response=RoleOut,
    auth=perm("authz.role.update"),
    summary="更新角色",
)
def update_role_api(request, role_id: int, payload: RoleUpdateIn):
    """更新角色基础信息."""
    try:
        role = update_role(
            role_id=role_id,
            role_name=payload.role_name,
            remark=payload.remark,
        )
    except RoleServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return role


@router.delete(
    "/authz/roles/{role_id}", auth=perm("authz.role.disable"), summary="停用角色"
)
def disable_role_api(request, role_id: int):
    """停用指定角色(软删)."""
    try:
        disable_role(role_id=role_id)
    except RoleServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {"success": True}
