from django.db import transaction
from django.utils import timezone

from apps.authz.models import SysPermissionSet, SysPermissionSetItem, SysResource


class PermissionSetServiceError(Exception):
    """权限集操作异常，携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


@transaction.atomic
def create_permission_set(
    *,
    set_code: str,
    set_name: str,
    realm: str,
    set_type: str,
    resource_codes: list[str] | None = None,
) -> SysPermissionSet:
    """创建权限集，可同时指定包含的资源."""
    if SysPermissionSet.objects.filter(set_code=set_code).exists():
        raise PermissionSetServiceError("SET_CODE_DUPLICATE")

    pset = SysPermissionSet.objects.create(
        set_code=set_code,
        set_name=set_name,
        realm=realm,
        set_type=set_type,
        version=1,
        status=1,
    )

    if resource_codes:
        _add_resources(pset, resource_codes)

    return pset


@transaction.atomic
def update_permission_set(
    *,
    set_id: int,
    set_name: str | None = None,
    resource_codes: list[str] | None = None,
) -> SysPermissionSet:
    """更新权限集名称和包含的资源."""
    pset = SysPermissionSet.objects.filter(id=set_id).first()
    if not pset:
        raise PermissionSetServiceError("SET_NOT_FOUND")

    if set_name is not None:
        pset.set_name = set_name
        pset.save(update_fields=["set_name"])

    if resource_codes is not None:
        # 覆盖式更新资源
        SysPermissionSetItem.objects.filter(set=pset).delete()
        _add_resources(pset, resource_codes)
        # 递增版本
        pset.version += 1
        pset.save(update_fields=["version"])

    return pset


@transaction.atomic
def disable_permission_set(*, set_id: int) -> SysPermissionSet:
    """停用权限集."""
    pset = SysPermissionSet.objects.filter(id=set_id).first()
    if not pset:
        raise PermissionSetServiceError("SET_NOT_FOUND")
    if pset.status == 0:
        raise PermissionSetServiceError("SET_ALREADY_DISABLED")

    pset.status = 0
    pset.save(update_fields=["status"])
    return pset


def get_permission_set_detail(set_id: int) -> tuple[SysPermissionSet, list[str]]:
    """获取权限集详情及其包含的资源码列表."""
    pset = SysPermissionSet.objects.filter(id=set_id).first()
    if not pset:
        raise PermissionSetServiceError("SET_NOT_FOUND")

    codes = list(
        SysPermissionSetItem.objects.filter(set=pset).values_list(
            "resource__resource_code", flat=True
        )
    )
    return pset, codes


def _add_resources(pset: SysPermissionSet, resource_codes: list[str]):
    """校验资源是否存在，并批量绑定到权限集."""
    resources = list(
        SysResource.objects.filter(resource_code__in=resource_codes, status=1)
    )
    if len(resources) != len(resource_codes):
        missing = set(resource_codes) - {r.resource_code for r in resources}
        raise PermissionSetServiceError(f"RESOURCE_NOT_FOUND:{sorted(missing)}")

    # 校验只读集规则：ps_hq_store_report_view 只能包含 QUERY 资源
    if pset.set_code == "ps_hq_store_report_view":
        for r in resources:
            if r.op_type != "QUERY":
                raise PermissionSetServiceError("READONLY_SET_VIOLATION")

    now = timezone.now()
    for r in resources:
        SysPermissionSetItem.objects.create(
            set=pset,
            resource=r,
            effect="ALLOW",
            granted_at=now,
        )
