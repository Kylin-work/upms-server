from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.authz.models import SysPermissionSet, SysRole, SysRolePermissionSet
from apps.support.models import SysPermVersion

ROLE_SETS = {
    "hq_dept_manager": ["ps_hq_dept_base", "ps_hq_store_report_view"],
    "hq_dept_staff": ["ps_hq_dept_base", "ps_hq_store_report_view"],
    "hq_purchaser": ["ps_hq_dept_base", "ps_hq_store_report_view"],
    "hq_finance_specialist": ["ps_hq_dept_base", "ps_hq_store_report_view"],
    "hq_warehouse_admin": ["ps_hq_dept_base", "ps_hq_store_report_view"],
    "hq_ops_manager": ["ps_hq_dept_base", "ps_hq_ops_manage"],
    "hq_ops_staff": ["ps_hq_dept_base", "ps_hq_store_report_view"],
    "direct_store_manager": ["ps_direct_store_full"],
    "direct_store_staff": ["ps_direct_store_readonly"],
    "franchise_admin": ["ps_franchise_store_admin"],
    "franchise_store_manager": ["ps_franchise_store_biz"],
    "franchise_store_staff": ["ps_franchise_store_biz"],
}


@transaction.atomic
def run():
    for role_code, set_codes in ROLE_SETS.items():
        role = SysRole.objects.filter(role_code=role_code).first()
        if role is None:
            raise CommandError(f"角色 {role_code} 不存在")
        for set_code in set_codes:
            pset = SysPermissionSet.objects.filter(set_code=set_code).first()
            if pset is None:
                raise CommandError(f"权限集 {set_code} 不存在")
            SysRolePermissionSet.objects.get_or_create(
                role=role,
                set=pset,
                defaults={"effect": "ALLOW", "priority": 0},
            )
    _assert()
    _bump_global_version()


def _assert():
    for role_code, set_codes in ROLE_SETS.items():
        role = SysRole.objects.get(role_code=role_code)
        bound = set(
            SysRolePermissionSet.objects.filter(role=role).values_list(
                "set__set_code", flat=True
            )
        )
        missing = set(set_codes) - bound
        if missing:
            raise CommandError(f"{role_code} 缺少权限集：{sorted(missing)}")


def _bump_global_version():
    now = timezone.now()
    _, created = SysPermVersion.objects.get_or_create(
        scope_key="GLOBAL",
        defaults={"version": 1, "updated_at": now},
    )
    if not created:
        SysPermVersion.objects.filter(scope_key="GLOBAL").update(
            version=F("version") + 1,
            updated_at=now,
        )
