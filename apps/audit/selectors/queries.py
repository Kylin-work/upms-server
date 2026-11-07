from django.db.models import QuerySet

from apps.audit.models import SysAuditGrantChange, SysAuditOperation


def query_operations(
    *,
    user_id: int | None = None,
    resource_code: str | None = None,
    result: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> QuerySet:
    """操作日志查询,按用户/资源码/结果/时间范围筛选."""
    qs = SysAuditOperation.objects.all().order_by("-id")
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if resource_code:
        qs = qs.filter(resource_code=resource_code)
    if result:
        qs = qs.filter(result=result)
    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end)
    return qs


def query_grant_changes(
    *,
    operator_id: int | None = None,
    target_type: str | None = None,
    change_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> QuerySet:
    """授权变更日志查询,按操作人/目标类型/变更类型/时间范围筛选."""
    qs = SysAuditGrantChange.objects.all().order_by("-id")
    if operator_id is not None:
        qs = qs.filter(operator_id=operator_id)
    if target_type:
        qs = qs.filter(target_type=target_type)
    if change_type:
        qs = qs.filter(change_type=change_type)
    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end)
    return qs
