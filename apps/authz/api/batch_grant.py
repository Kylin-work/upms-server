from ninja import Router, Schema
from pydantic import Field

from apps.authz.services.batch_grant import (
    BatchGrantError,
    dry_run,
    resolve_targets,
)
from apps.guard.services.perm import perm

router = Router(tags=["authz"])


class BatchGrantIn(Schema):
    mode: str
    org_code: str | None = None
    position_code: str | None = None
    usernames: list[str] = Field(default_factory=list)
    role_codes: list[str] = Field(default_factory=list)


class UserResult(Schema):
    user_id: int
    username: str
    reasons: list[str] = Field(default_factory=list)


class DryRunOut(Schema):
    affected_users: list[UserResult] = Field(default_factory=list)
    skipped_users: list[UserResult] = Field(default_factory=list)
    rejected_users: list[UserResult] = Field(default_factory=list)


@router.post(
    "/authz/user-roles/batch:dry-run",
    response=DryRunOut,
    auth=perm("authz.role.grant"),
)
def batch_grant_dry_run(request, payload: BatchGrantIn):
    try:
        targets = resolve_targets(
            mode=payload.mode,
            org_code=payload.org_code,
            position_code=payload.position_code,
            usernames=payload.usernames,
        )
        result = dry_run(
            target_users=targets,
            role_codes=payload.role_codes,
            operator=request.user,
        )
    except BatchGrantError as exc:
        from ninja.errors import HttpError

        status = (
            403 if exc.code in ("REALM_VIOLATION", "ROLE_NOT_GRANTABLE_LEVEL") else 400
        )
        raise HttpError(status, exc.code) from exc
    return {
        "affected_users": result.affected_users,
        "skipped_users": result.skipped_users,
        "rejected_users": result.rejected_users,
    }
