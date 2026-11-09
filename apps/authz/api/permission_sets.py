from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.authz.services.permission_set import (
    PermissionSetServiceError,
    create_permission_set,
    disable_permission_set,
    get_permission_set_detail,
    update_permission_set,
)
from apps.guard.services.perm import perm

router = Router(tags=["authz"])


class PermissionSetOut(Schema):
    id: int = Field(..., description="权限集ID")
    set_code: str = Field(..., description="权限集编码")
    set_name: str = Field(..., description="权限集名称")
    realm: str = Field(..., description="所属域")
    set_type: str = Field(..., description="类型")
    version: int = Field(..., description="版本号")
    status: int = Field(..., description="状态: 1启用, 0停用")
    resources: list[str] = Field(default_factory=list, description="包含的资源码列表")


class PermissionSetCreateIn(Schema):
    set_code: str = Field(..., description="权限集编码,全局唯一")
    set_name: str = Field(..., description="权限集名称")
    realm: str = Field(..., description="所属域")
    set_type: str = Field(..., description="类型")
    resource_codes: list[str] | None = Field(None, description="包含的资源码列表")


class PermissionSetUpdateIn(Schema):
    set_name: str | None = Field(None, description="权限集名称")
    resource_codes: list[str] | None = Field(None, description="覆盖式更新资源码列表")


@router.post("/authz/sets", response=PermissionSetOut, auth=perm("authz.set.create"), summary="创建权限集")
def create_set_api(request, payload: PermissionSetCreateIn):
    """创建单个权限集."""
    try:
        pset = create_permission_set(
            set_code=payload.set_code,
            set_name=payload.set_name,
            realm=payload.realm,
            set_type=payload.set_type,
            resource_codes=payload.resource_codes,
        )
        _, codes = get_permission_set_detail(pset.id)
    except PermissionSetServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": pset.id,
        "set_code": pset.set_code,
        "set_name": pset.set_name,
        "realm": pset.realm,
        "set_type": pset.set_type,
        "version": pset.version,
        "status": pset.status,
        "resources": codes,
    }


@router.get("/authz/sets/{set_id}", response=PermissionSetOut, auth=perm("authz.set.view"), summary="获取权限集详情")
def get_set_api(request, set_id: int):
    """根据 ID 查询权限集及包含的资源."""
    try:
        pset, codes = get_permission_set_detail(set_id)
    except PermissionSetServiceError as exc:
        raise HttpError(404, exc.code) from exc
    return {
        "id": pset.id,
        "set_code": pset.set_code,
        "set_name": pset.set_name,
        "realm": pset.realm,
        "set_type": pset.set_type,
        "version": pset.version,
        "status": pset.status,
        "resources": codes,
    }


@router.put("/authz/sets/{set_id}", response=PermissionSetOut, auth=perm("authz.set.update"), summary="更新权限集")
def update_set_api(request, set_id: int, payload: PermissionSetUpdateIn):
    """更新权限集名称和资源."""
    try:
        pset = update_permission_set(
            set_id=set_id,
            set_name=payload.set_name,
            resource_codes=payload.resource_codes,
        )
        _, codes = get_permission_set_detail(pset.id)
    except PermissionSetServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": pset.id,
        "set_code": pset.set_code,
        "set_name": pset.set_name,
        "realm": pset.realm,
        "set_type": pset.set_type,
        "version": pset.version,
        "status": pset.status,
        "resources": codes,
    }


@router.delete("/authz/sets/{set_id}", auth=perm("authz.set.disable"), summary="停用权限集")
def disable_set_api(request, set_id: int):
    """停用指定权限集(软删)."""
    try:
        disable_permission_set(set_id=set_id)
    except PermissionSetServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {"success": True}
