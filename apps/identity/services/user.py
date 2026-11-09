from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.authz.models import SysRole, SysUserRole
from apps.identity.models import SysUser, SysUserPosition
from apps.orgs.models import SysOrg, SysPosition


class UserServiceError(Exception):
    """用户操作异常，携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


DEFAULT_INITIAL_PASSWORD = "Init@123456"


@transaction.atomic
def create_user(
    *,
    username: str,
    real_name: str,
    org_code: str,
    position_code: str,
    mobile: str | None = None,
    email: str | None = None,
    role_codes: list[str] | None = None,
    operator_id: int,
) -> SysUser:
    """创建单个用户，包含绑定岗位与角色."""
    if SysUser.objects.filter(username=username).exists():
        raise UserServiceError("USERNAME_DUPLICATE")

    org = SysOrg.objects.filter(org_code=org_code, status=1).first()
    if not org:
        raise UserServiceError("ORG_NOT_FOUND")

    position = SysPosition.objects.filter(position_code=position_code, status=1).first()
    if not position:
        raise UserServiceError("POSITION_NOT_FOUND")

    # 校验岗位是否适用该组织类型
    scopes = {s.strip() for s in position.org_type_scope.split(",") if s.strip()}
    if org.org_type not in scopes:
        raise UserServiceError("POSITION_ORG_MISMATCH")

    # 确定 realm
    realm = "HQ"
    if org.org_type == "STORE_DIRECT":
        realm = "DIRECT"
    elif org.org_type == "STORE_FRANCHISE":
        realm = "FRANCHISE"

    # 处理角色
    roles = []
    if role_codes:
        roles = list(SysRole.objects.filter(role_code__in=role_codes, status=1))
        if len(roles) != len(role_codes):
            raise UserServiceError("ROLE_NOT_FOUND")
        for r in roles:
            if r.realm != realm:
                raise UserServiceError("REALM_MISMATCH")
    else:
        # 没传角色则用岗位默认角色
        default_codes = position.default_role_codes or []
        if default_codes:
            roles = list(
                SysRole.objects.filter(
                    role_code__in=default_codes, realm=realm, status=1
                )
            )

    now = timezone.now()
    user = SysUser.objects.create(
        username=username,
        employee_no=username,
        real_name=real_name,
        mobile=mobile,
        email=email,
        password_hash=make_password(DEFAULT_INITIAL_PASSWORD),
        org=org,
        position=position,
        realm=realm,
        store=org if org.org_type in ("STORE_DIRECT", "STORE_FRANCHISE") else None,
        is_platform_admin=False,
        status=1,
        pwd_updated_at=now,
        created_at=now,
        updated_at=now,
    )

    SysUserPosition.objects.create(
        user=user,
        org=org,
        position=position,
        is_primary=True,
    )

    for r in roles:
        SysUserRole.objects.create(
            user=user,
            role=r,
            granted_by=operator_id,
            granted_at=now,
            source="MANUAL",
        )

    return user


@transaction.atomic
def update_user(
    *,
    user_id: int,
    real_name: str | None = None,
    mobile: str | None = None,
    email: str | None = None,
) -> SysUser:
    """更新用户基础信息（不允许直接改组织和角色）."""
    user = SysUser.objects.filter(id=user_id, status=1).first()
    if not user:
        raise UserServiceError("USER_NOT_FOUND")

    update_fields = ["updated_at"]
    if real_name is not None:
        user.real_name = real_name
        update_fields.append("real_name")
    if mobile is not None:
        user.mobile = mobile
        update_fields.append("mobile")
    if email is not None:
        user.email = email
        update_fields.append("email")

    user.updated_at = timezone.now()
    user.save(update_fields=update_fields)
    return user


@transaction.atomic
def disable_user(*, user_id: int) -> SysUser:
    """停用用户（软删）."""
    user = SysUser.objects.filter(id=user_id).first()
    if not user:
        raise UserServiceError("USER_NOT_FOUND")
    if user.status == 0:
        raise UserServiceError("USER_ALREADY_DISABLED")

    user.status = 0
    user.updated_at = timezone.now()
    user.save(update_fields=["status", "updated_at"])
    return user


def get_user_detail(user_id: int, scope: dict | None) -> SysUser:
    """获取用户详情，并套用数据范围过滤."""

    qs = SysUser.objects.filter(id=user_id)
    # 这里借用 apply_data_scope，但由于 sys_user 的字段是 org_id，需要指定
    # 简化起见，直接查 org 的路径前缀
    if scope and scope.get("type") == "ORG_TREE":
        prefixes = scope.get("path_prefixes", [])
        if prefixes:
            from django.db.models import Q

            q = Q()
            for p in prefixes:
                q |= Q(org__path__startswith=p)
            qs = qs.filter(q)
        else:
            qs = qs.none()
    elif scope and scope.get("type") == "NONE":
        qs = qs.none()

    user = qs.first()
    if not user:
        raise UserServiceError("USER_NOT_FOUND")
    return user
