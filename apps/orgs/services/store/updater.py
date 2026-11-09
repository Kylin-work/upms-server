import uuid

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_operation
from apps.orgs.models import SysOrg

from .errors import StoreServiceError


@transaction.atomic
def update_store(
    *,
    store_id: int,
    org_name: str | None = None,
    operator_id: int,
    trace_id: str | None = None,
    request_path: str = "",
    ip: str | None = None,
) -> SysOrg:
    """更新门店基础信息,只允许改 org_name."""
    store = SysOrg.objects.filter(
        id=store_id, org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"]
    ).first()
    if store is None:
        raise StoreServiceError("STORE_NOT_FOUND")
    if org_name is not None:
        store.org_name = org_name
        store.updated_at = timezone.now()
        store.save(update_fields=["org_name", "updated_at"])
    log_operation(
        trace_id=trace_id or uuid.uuid4().hex,
        user_id=operator_id,
        username=None,
        module="orgs",
        resource_code="org.store.create",
        http_method="PUT",
        request_path=request_path,
        result="SUCCESS",
        target_type="STORE",
        target_id=store.id,
        target_org_id=store.id,
        ip=ip,
    )
    return store
