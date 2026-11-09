from apps.guard.selectors.filters import apply_data_scope
from apps.orgs.models import SysOrg
from apps.orgs.services.store.errors import StoreServiceError


def get_store(store_id: int, scope: dict | None) -> SysOrg:
    """按 id 查门店,并套数据范围过滤."""
    qs = SysOrg.objects.filter(
        id=store_id, org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"]
    )
    qs = apply_data_scope(qs, scope, org_field="path")
    store = qs.first()
    if store is None:
        raise StoreServiceError("STORE_NOT_FOUND")
    return store


def list_stores(scope: dict | None):
    """查询门店列表,按数据范围过滤,只返回启用的."""
    qs = SysOrg.objects.filter(
        org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"], status=1
    )
    qs = apply_data_scope(qs, scope, org_field="path")
    return qs.order_by("id")
