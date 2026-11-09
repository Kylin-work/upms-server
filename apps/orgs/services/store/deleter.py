import uuid

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_operation
from apps.orgs.models import SysOrg

from .errors import StoreServiceError


@transaction.atomic
def disable_store(
    *,
    store_id: int,
    operator_id: int,
    trace_id: str | None = None,
    request_path: str = "",
    ip: str | None = None,
) -> SysOrg:
    """停用门店,软删,status 置 0."""
    store = SysOrg.objects.filter(
        id=store_id, org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"]
    ).first()
    if store is None:
        raise StoreServiceError("STORE_NOT_FOUND")
    if store.status == 0:
        raise StoreServiceError("STORE_ALREADY_DISABLED")
    store.status = 0
    store.updated_at = timezone.now()
    store.save(update_fields=["status", "updated_at"])
    log_operation(
        trace_id=trace_id or uuid.uuid4().hex,
        user_id=operator_id,
        username=None,
        module="orgs",
        resource_code="org.store.create",
        http_method="DELETE",
        request_path=request_path,
        result="SUCCESS",
        target_type="STORE",
        target_id=store.id,
        target_org_id=store.id,
        ip=ip,
    )
    return store
