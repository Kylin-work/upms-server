import uuid

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_operation
from apps.orgs.models import SysOrg, SysOrgPosition, SysPosition


class StoreCreateError(Exception):
    """建店失败，携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


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
        raise StoreCreateError("INVALID_ORG_TYPE")

    if SysOrg.objects.filter(org_code=org_code).exists():
        raise StoreCreateError("ORG_CODE_DUPLICATE")

    parent = SysOrg.objects.filter(org_code=parent_code).first()
    if parent is None:
        raise StoreCreateError("PARENT_NOT_FOUND")
    # 门店只能挂在运营部下,设计 4.1 的 4.b 强校验
    if parent.dept_code != "OPS":
        raise StoreCreateError("PARENT_NOT_OPS")

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
            raise StoreCreateError(f"POSITION_NOT_FOUND:{pos_code}")
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
        raise StoreCreateError("STORE_NOT_FOUND")
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
        raise StoreCreateError("STORE_NOT_FOUND")
    if store.status == 0:
        raise StoreCreateError("STORE_ALREADY_DISABLED")
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


def get_store(store_id: int, scope: dict | None) -> SysOrg:
    """按 id 查门店,并套数据范围过滤."""
    from apps.guard.selectors.filters import apply_data_scope

    qs = SysOrg.objects.filter(
        id=store_id, org_type__in=["STORE_DIRECT", "STORE_FRANCHISE"]
    )
    qs = apply_data_scope(qs, scope, org_field="path")
    store = qs.first()
    if store is None:
        raise StoreCreateError("STORE_NOT_FOUND")
    return store
