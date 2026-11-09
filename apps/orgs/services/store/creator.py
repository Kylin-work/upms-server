import uuid

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_operation
from apps.orgs.models import SysOrg, SysOrgPosition, SysPosition

from .errors import StoreServiceError

# 门店类型到岗位编码的映射,直营两岗,加盟三岗
STORE_POSITIONS = {
    "STORE_DIRECT": ["STORE_MGR", "STORE_STAFF"],
    "STORE_FRANCHISE": ["FRANCHISE_ADMIN", "STORE_MGR", "STORE_STAFF"],
}

# 门店类型到 store_type 字段值的映射
STORE_TYPE_VALUE = {
    "STORE_DIRECT": "DIRECT",
    "STORE_FRANCHISE": "FRANCHISE",
}


@transaction.atomic
def create_store(
    *,
    org_code: str,
    org_name: str,
    org_type: str,
    parent_code: str,
    operator_id: int,
    trace_id: str | None = None,
    request_path: str = "",
    ip: str | None = None,
) -> SysOrg:
    """创建单个门店,含 path 回填、岗位实例化、审计写入."""
    if org_type not in STORE_TYPE_VALUE:
        raise StoreServiceError("INVALID_ORG_TYPE")

    if SysOrg.objects.filter(org_code=org_code).exists():
        raise StoreServiceError("ORG_CODE_DUPLICATE")

    parent = SysOrg.objects.filter(org_code=parent_code).first()
    if parent is None:
        raise StoreServiceError("PARENT_NOT_FOUND")
    # 门店只能挂在运营部下,设计 4.1 的 4.b 强校验
    if parent.dept_code != "OPS":
        raise StoreServiceError("PARENT_NOT_OPS")

    now = timezone.now()
    store = SysOrg.objects.create(
        parent=parent,
        org_code=org_code,
        org_name=org_name,
        org_type=org_type,
        path="/",
        level=parent.level + 1,
        store_type=STORE_TYPE_VALUE[org_type],
        manage_owner_type="COMPANY"
        if org_type == "STORE_DIRECT"
        else "FRANCHISE_OWNER",
        status=1,
        sort_no=0,
        created_at=now,
        updated_at=now,
    )
    # 先插占位 path 再回填,与设计 4.1 的 4.d 一致
    store.path = f"{parent.path}{store.id}/"
    store.save(update_fields=["path"])

    # 按门店类型实例化岗位
    for pos_code in STORE_POSITIONS[org_type]:
        pos = SysPosition.objects.filter(position_code=pos_code).first()
        if pos is None:
            raise StoreServiceError(f"POSITION_NOT_FOUND:{pos_code}")
        SysOrgPosition.objects.get_or_create(
            org=store,
            position=pos,
            defaults={"headcount": 0, "status": 1},
        )

    # 写操作审计,resource_code 对应 org.store.create
    log_operation(
        trace_id=trace_id or uuid.uuid4().hex,
        user_id=operator_id,
        username=None,
        module="orgs",
        resource_code="org.store.create",
        http_method="POST",
        request_path=request_path,
        result="SUCCESS",
        target_type="STORE",
        target_id=store.id,
        target_org_id=store.id,
        ip=ip,
    )
    return store
