import uuid
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.audit.services import log_grant_change
from apps.authz.models import SysRole, SysUserRole
from apps.authz.services.grant import _operator_levels, can_grant
from apps.identity.models import SysUser
from apps.orgs.models import SysOrg
from apps.support.models import SysPermVersion


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


@dataclass
class ExecuteResult:
    batch_id: str
    affected_count: int
    skipped_count: int
    rejected_count: int


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
            org__path__startswith=org.path, status=1,
        )
    elif mode == "position":
        if not position_code:
            raise BatchGrantError("POSITION_CODE_REQUIRED")
        users = SysUser.objects.filter(
            position__position_code=position_code, status=1,
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

    for role in roles:
        _check_realm_grantable(operator, role)

    result = DryRunResult()
    for user in target_users:
        status, reasons = _classify_user(user, roles, operator)
        entry = {"user_id": user.id, "username": user.username, "reasons": reasons}
        if status == "affected":
            result.affected_users.append(entry)
        elif status == "skipped":
            result.skipped_users.append(entry)
        else:
            result.rejected_users.append(entry)
    return result


@transaction.atomic
def execute(
    *,
    target_users: list[SysUser],
    role_codes: list[str],
    operator,
    reason: str,
) -> ExecuteResult:
    """正式执行批量授权,分页 upsert,写审计与版本号."""
    roles = list(SysRole.objects.filter(role_code__in=role_codes, status=1))
    if len(roles) != len(role_codes):
        raise BatchGrantError("ROLE_NOT_FOUND")

    for role in roles:
        _check_realm_grantable(operator, role)

    batch_id = uuid.uuid4().hex
    now = timezone.now()
    affected_count = 0
    skipped_count = 0
    rejected_count = 0

    # 收集要插入的记录和要失效的用户
    to_insert = []
    affected_user_ids = []
    detail_summary = []

    for user in target_users:
        status, reasons = _classify_user(user, roles, operator)
        if status == "skipped":
            skipped_count += 1
            detail_summary.append(f"user:{user.id}=SKIP")
            continue
        if status == "rejected":
            rejected_count += 1
            detail_summary.append(f"user:{user.id}=REJECT({','.join(reasons)})")
            continue

        for role in roles:
            to_insert.append(
                SysUserRole(
                    user=user,
                    role=role,
                    granted_by=operator.id,
                    granted_at=now,
                    source="BATCH",
                    batch_id=batch_id,
                )
            )
        affected_user_ids.append(user.id)
        affected_count += 1
        detail_summary.append(f"user:{user.id}=AFFECTED")

    # 分页批量插入（每批 500 条）
    BATCH_SIZE = 500
    for i in range(0, len(to_insert), BATCH_SIZE):
        chunk = to_insert[i:i + BATCH_SIZE]
        SysUserRole.objects.bulk_create(chunk, ignore_conflicts=True)

    # 递增受影响用户的版本号
    for uid in affected_user_ids:
        _bump_version(f"USER:{uid}", now)
    _bump_version("GLOBAL", now)

    # 写入聚合审计，并附带限制长度的逐用户明细摘要
    # 考虑到 sys_audit_grant_change.diff_summary 只有 512 字节，超出部分截断
    summary = f"affected={affected_count},skipped={skipped_count},rejected={rejected_count} | " + ";".join(detail_summary)
    if len(summary) > 512:
        summary = summary[:509] + "..."

    log_grant_change(
        trace_id=uuid.uuid4().hex,
        operator_id=operator.id,
        change_type="GRANT",
        target_type="USER",
        target_id=0,
        reason=reason,
        diff_summary=summary,
        batch_id=batch_id,
    )

    return ExecuteResult(
        batch_id=batch_id,
        affected_count=affected_count,
        skipped_count=skipped_count,
        rejected_count=rejected_count,
    )


def _check_realm_grantable(operator, role: SysRole) -> None:
    if operator.is_platform_admin:
        return
    if role.assignable_level not in _operator_levels(operator):
        raise BatchGrantError("ROLE_NOT_GRANTABLE_LEVEL")
    if role.realm != operator.realm:
        raise BatchGrantError("REALM_VIOLATION")


def _classify_user(user: SysUser, roles: list[SysRole], operator) -> tuple[str, list[str]]:
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
        SysUserRole.objects.filter(user=user, role__in=roles)
        .values_list("role_id", flat=True)
    )
    if len(existing) == len(roles):
        return "skipped", ["ALREADY_GRANTED"]
    return "affected", []


def _bump_version(scope_key: str, now) -> None:
    _, created = SysPermVersion.objects.get_or_create(
        scope_key=scope_key,
        defaults={"version": 1, "updated_at": now},
    )
    if not created:
        SysPermVersion.objects.filter(scope_key=scope_key).update(
            version=F("version") + 1, updated_at=now,
        )
