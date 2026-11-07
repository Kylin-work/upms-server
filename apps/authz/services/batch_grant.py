from dataclasses import dataclass, field

from apps.authz.models import SysRole, SysUserRole
from apps.authz.services.grant import _operator_levels, can_grant
from apps.identity.models import SysUser
from apps.orgs.models import SysOrg


class BatchGrantError(Exception):
    """批量授权失败,携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


@dataclass
class DryRunResult:
    affected_users: list[dict] = field(default_factory=list)
    skipped_users: list[dict] = field(default_factory=list)
    rejected_users: list[dict] = field(default_factory=list)


def resolve_targets(
    *,
    mode: str,
    org_code: str | None = None,
    position_code: str | None = None,
    usernames: list[str] | None = None,
) -> list[SysUser]:
    """按组织子树/岗位/名单解析目标用户集合."""
    if mode == "org_subtree":
        if not org_code:
            raise BatchGrantError("ORG_CODE_REQUIRED")
        org = SysOrg.objects.filter(org_code=org_code).first()
        if org is None:
            raise BatchGrantError("ORG_NOT_FOUND")
        users = SysUser.objects.filter(
            org__path__startswith=org.path,
            status=1,
        )
    elif mode == "position":
        if not position_code:
            raise BatchGrantError("POSITION_CODE_REQUIRED")
        users = SysUser.objects.filter(
            position__position_code=position_code,
            status=1,
        )
    elif mode == "usernames":
        if not usernames:
            raise BatchGrantError("USERNAMES_REQUIRED")
        users = SysUser.objects.filter(username__in=usernames, status=1)
    else:
        raise BatchGrantError("INVALID_MODE")
    return list(users)


def dry_run(
    *,
    target_users: list[SysUser],
    role_codes: list[str],
    operator,
) -> DryRunResult:
    """预演批量授权,不写库,返回三组结果."""
    roles = list(SysRole.objects.filter(role_code__in=role_codes, status=1))
    if len(roles) != len(role_codes):
        raise BatchGrantError("ROLE_NOT_FOUND")

    result = DryRunResult()
    for role in roles:
        _check_realm_grantable(operator, role)

    for user in target_users:
        user_result = _classify_user(user, roles, operator)
        if user_result[0] == "affected":
            result.affected_users.append(
                {"user_id": user.id, "username": user.username, "reasons": []}
            )
        elif user_result[0] == "skipped":
            result.skipped_users.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "reasons": user_result[1],
                }
            )
        else:
            result.rejected_users.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "reasons": user_result[1],
                }
            )
    return result


def _check_realm_grantable(operator, role: SysRole) -> None:
    if operator.is_platform_admin:
        return
    if role.assignable_level not in _operator_levels(operator):
        raise BatchGrantError("ROLE_NOT_GRANTABLE_LEVEL")
    if role.realm != operator.realm:
        raise BatchGrantError("REALM_VIOLATION")


def _classify_user(
    user: SysUser, roles: list[SysRole], operator
) -> tuple[str, list[str]]:
    """单用户分类:affected / skipped / rejected,附原因列表."""
    rejected: list[str] = []
    for role in roles:
        if not can_grant(operator, role, []):
            rejected.append("GRANT_EXCEED_AUTHORITY")
            break
        if role.realm != user.realm:
            rejected.append("REALM_MISMATCH")
            break
    if rejected:
        return "rejected", rejected

    existing = set(
        SysUserRole.objects.filter(user=user, role__in=roles).values_list(
            "role_id", flat=True
        )
    )
    if len(existing) == len(roles):
        return "skipped", ["ALREADY_GRANTED"]
    return "affected", []
