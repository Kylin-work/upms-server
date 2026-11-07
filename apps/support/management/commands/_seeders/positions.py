from django.core.management.base import CommandError
from django.db import transaction

from apps.orgs.models import SysPosition

POSITIONS = [
    ("DEPT_MGR", "部门管理岗", "DEPT", True, ["hq_dept_manager"]),
    ("DEPT_STAFF", "部门普通员工", "DEPT", False, ["hq_dept_staff"]),
    (
        "STORE_MGR",
        "店长",
        "STORE_DIRECT,STORE_FRANCHISE",
        True,
        ["direct_store_manager", "franchise_store_manager"],
    ),
    (
        "STORE_STAFF",
        "店员",
        "STORE_DIRECT,STORE_FRANCHISE",
        False,
        ["direct_store_staff", "franchise_store_staff"],
    ),
    (
        "FRANCHISE_ADMIN",
        "加盟店老板/管理员",
        "STORE_FRANCHISE",
        True,
        ["franchise_admin"],
    ),
]


@transaction.atomic
def run():
    for code, name, scope, is_mgr, role_codes in POSITIONS:
        if not SysPosition.objects.filter(position_code=code).exists():
            SysPosition.objects.create(
                position_code=code,
                position_name=name,
                org_type_scope=scope,
                is_management=is_mgr,
                default_role_codes=role_codes,
                status=1,
            )
    _assert()


def _assert():
    expected = {p[0] for p in POSITIONS}
    actual = set(
        SysPosition.objects.filter(position_code__in=expected).values_list(
            "position_code", flat=True
        )
    )
    missing = expected - actual
    if missing:
        raise CommandError(f"岗位缺失：{sorted(missing)}")
