import uuid

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.guard.selectors.filters import apply_data_scope
from apps.guard.services.perm import perm
from apps.orgs.models import SysOrg
from apps.orgs.services.store import StoreCreateError, create_store

router = Router(tags=["orgs"])


class StoreOut(Schema):
    id: int
    org_code: str
    org_name: str
    org_type: str
    path: str


class StoreCreateIn(Schema):
    org_code: str
    org_name: str
    org_type: str
    parent_code: str = "DEPT_OPS"


@router.get("/orgs/stores", response=list[StoreOut], auth=perm("org.store.list"))
def list_stores(request):
    qs = SysOrg.objects.filter(org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"])
    scope = request.ctx_data_scope
    qs = apply_data_scope(qs, scope, org_field="path")
    return list(
        qs.order_by("id").values("id", "org_code", "org_name", "org_type", "path")
    )


@router.post("/orgs/stores", response=StoreOut, auth=perm("org.store.create"))
def create_store_api(request, payload: StoreCreateIn):
    try:
        store = create_store(
            org_code=payload.org_code,
            org_name=payload.org_name,
            org_type=payload.org_type,
            parent_code=payload.parent_code,
            operator_id=request.user.id,
            trace_id=uuid.uuid4().hex,
            request_path=request.path,
            ip=_client_ip(request),
        )
    except StoreCreateError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": store.id,
        "org_code": store.org_code,
        "org_name": store.org_name,
        "org_type": store.org_type,
        "path": store.path,
    }


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
