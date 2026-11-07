import uuid

from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.authz.services.grant import GrantError, grant_role
from apps.guard.services.perm import perm

router = Router(tags=["authz"])


class GrantIn(Schema):
    set_codes: list[str] = Field(default_factory=list)
    resource_codes: list[str] = Field(default_factory=list)
    reason: str


class GrantOut(Schema):
    role_id: int
    added_sets: list[str]
    removed_sets: list[str]
    added_resources: list[str]
    removed_resources: list[str]


@router.post(
    "/authz/roles/{role_id}/grants",
    response=GrantOut,
    auth=perm("authz.role.grant"),
)
def grant_role_api(request, role_id: int, payload: GrantIn):
    if not payload.reason.strip():
        raise HttpError(400, "REASON_REQUIRED")
    try:
        result = grant_role(
            role_id=role_id,
            set_codes=payload.set_codes,
            resource_codes=payload.resource_codes,
            reason=payload.reason,
            operator=request.user,
            trace_id=uuid.uuid4().hex,
        )
    except GrantError as exc:
        status = 403 if exc.code == "GRANT_EXCEED_AUTHORITY" else 400
        raise HttpError(status, exc.code) from exc
    return {
        "role_id": result.role_id,
        "added_sets": result.added_sets,
        "removed_sets": result.removed_sets,
        "added_resources": result.added_resources,
        "removed_resources": result.removed_resources,
    }
