from datetime import datetime

from ninja import Router, Schema
from pydantic import Field

from apps.audit.selectors.queries import query_grant_changes, query_operations
from apps.guard.services.perm import perm

router = Router(tags=["audit"])


class OperationOut(Schema):
    id: int
    trace_id: str
    user_id: int | None
    username: str
    module: str
    resource_code: str
    http_method: str
    request_path: str
    result: str
    error_code: str | None
    cost_ms: int | None
    target_type: str | None
    target_id: int | None
    created_at: datetime


class GrantChangeOut(Schema):
    id: int
    trace_id: str
    operator_id: int
    change_type: str
    target_type: str
    target_id: int
    before_snapshot: dict | None
    after_snapshot: dict | None
    diff_summary: str | None
    reason: str
    batch_id: str | None
    created_at: datetime


class PageOut(Schema):
    items: list[dict] = Field(default_factory=list)
    total: int


@router.get("/audit/operations", response=PageOut, auth=perm("audit.operation.query"))
def list_operations(
    request,
    user_id: int | None = None,
    resource_code: str | None = None,
    result: str | None = None,
    start: str | None = None,
    end: str | None = None,
    offset: int = 0,
    limit: int = 50,
):
    # 操作日志查询,分页返回
    qs = query_operations(
        user_id=user_id,
        resource_code=resource_code,
        result=result,
        start=start,
        end=end,
    )
    total = qs.count()
    items = list(qs[offset : offset + limit].values())
    return {"items": items, "total": total}


@router.get("/audit/grant-changes", response=PageOut, auth=perm("audit.grant.query"))
def list_grant_changes(
    request,
    operator_id: int | None = None,
    target_type: str | None = None,
    change_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
    offset: int = 0,
    limit: int = 50,
):
    # 授权变更日志查询,分页返回
    qs = query_grant_changes(
        operator_id=operator_id,
        target_type=target_type,
        change_type=change_type,
        start=start,
        end=end,
    )
    total = qs.count()
    items = list(qs[offset : offset + limit].values())
    return {"items": items, "total": total}
