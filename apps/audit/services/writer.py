from django.utils import timezone

from apps.audit.models import (
    SysAuditGrantChange,
    SysAuditLogin,
    SysAuditOperation,
)
from apps.identity.models import SysUser  # 新增导入


def log_login(
    *,
    user_id: int | None,
    username: str,
    login_type: str,
    login_result: str,
    fail_reason: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    SysAuditLogin.objects.create(
        user_id=user_id,
        username=username,
        login_type=login_type,
        login_result=login_result,
        fail_reason=fail_reason,
        ip=ip,
        user_agent=user_agent,
        created_at=timezone.now(),
    )


def log_operation(
    *,
    trace_id: str,
    user_id: int | None,
    username: str | None = None,  # 改为可选，如果传了空则自动查库
    module: str,
    resource_code: str,
    http_method: str,
    request_path: str,
    result: str,
    params_digest: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    target_org_id: int | None = None,
    error_code: str | None = None,
    cost_ms: int | None = None,
    ip: str | None = None,
) -> None:
    # 如果没有传 username 且有 user_id，则自动去查库获取
    if not username and user_id:
        u = SysUser.objects.filter(id=user_id).only("username").first()
        if u:
            username = u.username

    # 如果查库也没有（如系统自动执行），则兜底
    if not username:
        username = "SYSTEM"

    SysAuditOperation.objects.create(
        trace_id=trace_id,
        user_id=user_id,
        username=username,
        module=module,
        resource_code=resource_code,
        http_method=http_method,
        request_path=request_path,
        params_digest=params_digest,
        target_type=target_type,
        target_id=target_id,
        target_org_id=target_org_id,
        result=result,
        error_code=error_code,
        cost_ms=cost_ms,
        ip=ip,
        created_at=timezone.now(),
    )


def log_grant_change(
    *,
    trace_id: str,
    operator_id: int,
    change_type: str,
    target_type: str,
    target_id: int,
    reason: str,
    before_snapshot: dict | None = None,
    after_snapshot: dict | None = None,
    diff_summary: str | None = None,
    batch_id: str | None = None,
) -> None:
    SysAuditGrantChange.objects.create(
        trace_id=trace_id,
        operator_id=operator_id,
        change_type=change_type,
        target_type=target_type,
        target_id=target_id,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        diff_summary=diff_summary,
        reason=reason,
        batch_id=batch_id,
        created_at=timezone.now(),
    )
