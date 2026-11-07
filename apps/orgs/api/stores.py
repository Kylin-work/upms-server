import uuid

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.guard.selectors.filters import apply_data_scope
from apps.guard.services.perm import perm
from apps.orgs.models import SysOrg
from apps.orgs.services.store import (
    StoreCreateError,
    create_store,
    disable_store,
    get_store,
    update_store,
)

router = Router(tags=["orgs"])


class StoreOut(Schema):
    id: int
    org_code: str
    org_name: str
    org_type: str
    status: int
    path: str


class StoreCreateIn(Schema):
    org_code: str
    org_name: str
    org_type: str
    parent_code: str = "DEPT_OPS"


class StoreUpdateIn(Schema):
    org_name: str | None = None


@router.get("/orgs/stores", response=list[StoreOut], auth=perm("org.store.list"))
def list_stores(request):
    qs = SysOrg.objects.filter(
        org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"], status=1
    )
    scope = request.ctx_data_scope
    qs = apply_data_scope(qs, scope, org_field="path")
    return list(
        qs.order_by("id").values(
            "id", "org_code", "org_name", "org_type", "status", "path"
        )
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
        "status": store.status,
        "path": store.path,
    }


@router.get("/orgs/stores/{store_id}", response=StoreOut, auth=perm("org.store.list"))
def get_store_api(request, store_id: int):
    try:
        store = get_store(store_id, request.ctx_data_scope)
    except StoreCreateError as exc:
        raise HttpError(404, exc.code) from exc
    return {
        "id": store.id,
        "org_code": store.org_code,
        "org_name": store.org_name,
        "org_type": store.org_type,
        "status": store.status,
        "path": store.path,
    }


@router.put("/orgs/stores/{store_id}", response=StoreOut, auth=perm("org.store.create"))
def update_store_api(request, store_id: int, payload: StoreUpdateIn):
    try:
        store = update_store(
            store_id=store_id,
            org_name=payload.org_name,
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
        "status": store.status,
        "path": store.path,
    }


@router.delete("/orgs/stores/{store_id}", auth=perm("org.store.create"))
def disable_store_api(request, store_id: int):
    try:
        disable_store(
            store_id=store_id,
            operator_id=request.user.id,
            trace_id=uuid.uuid4().hex,
            request_path=request.path,
            ip=_client_ip(request),
        )
    except StoreCreateError as exc:
        raise HttpError(400, exc.code) from exc
    return {"success": True}


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
