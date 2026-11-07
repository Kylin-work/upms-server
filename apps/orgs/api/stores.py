from ninja import Router, Schema

from apps.guard.selectors.filters import apply_data_scope
from apps.guard.services.perm import perm
from apps.orgs.models import SysOrg

router = Router(tags=["orgs"])


class StoreOut(Schema):
    id: int
    org_code: str
    org_name: str
    org_type: str
    path: str


@router.get("/orgs/stores", response=list[StoreOut], auth=perm("org.store.list"))
def list_stores(request):
    qs = SysOrg.objects.filter(org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"])
    scope = request.ctx_data_scope
    qs = apply_data_scope(qs, scope, org_field="path")
    return list(
        qs.order_by("id").values("id", "org_code", "org_name", "org_type", "path")
    )
