from django.db import transaction

from apps.authz.models import SysRole
from apps.orgs.models import SysOrg


class RoleServiceError(Exception):
    """角色操作异常，携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


@transaction.atomic
def create_role(
    *,
    role_code: str,
    role_name: str,
    realm: str,
    role_type: str,
    data_scope_type: str,
    assignable_level: str,
    org_code: str | None = None,
    remark: str | None = None,
) -> SysRole:
    """创建角色."""
    if SysRole.objects.filter(role_code=role_code).exists():
        raise RoleServiceError("ROLE_CODE_DUPLICATE")

    org_id = None
    if org_code:
        org = SysOrg.objects.filter(org_code=org_code, status=1).first()
        if not org:
            raise RoleServiceError("ORG_NOT_FOUND")
        org_id = org.id

    # 简单校验 realm 一致性
    if role_type == "FUNC_BIZ" and not org_id:
        raise RoleServiceError("FUNC_BIZ_REQUIRE_ORG")

    role = SysRole.objects.create(
        role_code=role_code,
        role_name=role_name,
        realm=realm,
        role_type=role_type,
        data_scope_type=data_scope_type,
        assignable_level=assignable_level,
        org_id=org_id,
        is_builtin=False,
        status=1,
        remark=remark,
    )
    return role


@transaction.atomic
def update_role(
    *,
    role_id: int,
    role_name: str | None = None,
    remark: str | None = None,
) -> SysRole:
    """更新角色基础信息（code 和 realm 不允许改）."""
    role = SysRole.objects.filter(id=role_id).first()
    if not role:
        raise RoleServiceError("ROLE_NOT_FOUND")
    if role.is_builtin:
        raise RoleServiceError("BUILTIN_ROLE_CANNOT_MODIFY")

    update_fields = []
    if role_name is not None:
        role.role_name = role_name
        update_fields.append("role_name")
    if remark is not None:
        role.remark = remark
        update_fields.append("remark")

    if update_fields:
        role.save(update_fields=update_fields)
    return role


@transaction.atomic
def disable_role(*, role_id: int) -> SysRole:
    """停用角色（软删）."""
    role = SysRole.objects.filter(id=role_id).first()
    if not role:
        raise RoleServiceError("ROLE_NOT_FOUND")
    if role.is_builtin:
        raise RoleServiceError("BUILTIN_ROLE_CANNOT_DISABLE")
    if role.status == 0:
        raise RoleServiceError("ROLE_ALREADY_DISABLED")

    role.status = 0
    role.save(update_fields=["status"])
    return role


def get_role_detail(role_id: int, scope: dict | None) -> SysRole:
    """获取角色详情（角色表本不受组织范围影响，但为统一接口保留签名）."""
    role = SysRole.objects.filter(id=role_id).first()
    if not role:
        raise RoleServiceError("ROLE_NOT_FOUND")
    return role
