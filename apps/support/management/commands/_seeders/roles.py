from django.core.management.base import CommandError
from django.db import transaction

from apps.authz.models import SysRole
from apps.orgs.models import SysOrg

ROLES = [
    (
        "platform_super_admin",
        "平台超级管理员",
        "PLATFORM",
        "ALL",
        "PLATFORM",
        "HQ",
        None,
    ),
    (
        "hq_dept_manager",
        "总部部门管理岗",
        "FUNC_BASE",
        "ORG_SUBTREE",
        "DEPT",
        "HQ",
        None,
    ),
    (
        "hq_dept_staff",
        "总部部门普通员工",
        "FUNC_BASE",
        "ORG_SUBTREE",
        "DEPT",
        "HQ",
        None,
    ),
    ("hq_purchaser", "采购员", "FUNC_BIZ", "ORG_SUBTREE", "DEPT", "HQ", "DEPT_PUR"),
    (
        "hq_finance_specialist",
        "财务专员",
        "FUNC_BIZ",
        "ORG_SUBTREE",
        "DEPT",
        "HQ",
        "DEPT_FIN",
    ),
    (
        "hq_warehouse_admin",
        "仓储管理员",
        "FUNC_BIZ",
        "ORG_SUBTREE",
        "DEPT",
        "HQ",
        "DEPT_WHS",
    ),
    ("hq_ops_manager", "运营部管理岗", "OPS", "ORG_SUBTREE", "DEPT", "HQ", None),
    ("hq_ops_staff", "运营部普通员工", "OPS", "ORG_SUBTREE", "DEPT", "HQ", None),
    ("direct_store_manager", "直营店长", "STORE", "ORG_SELF", "STORE", "DIRECT", None),
    ("direct_store_staff", "直营店员", "STORE", "SELF_ONLY", "STORE", "DIRECT", None),
    (
        "franchise_admin",
        "加盟店老板/管理员",
        "STORE",
        "ORG_SELF",
        "STORE",
        "FRANCHISE",
        None,
    ),
    (
        "franchise_store_manager",
        "加盟店长",
        "STORE",
        "ORG_SELF",
        "STORE",
        "FRANCHISE",
        None,
    ),
    (
        "franchise_store_staff",
        "加盟店员",
        "STORE",
        "SELF_ONLY",
        "STORE",
        "FRANCHISE",
        None,
    ),
]


@transaction.atomic
def run():
    for code, name, role_type, scope_type, level, realm, org_code in ROLES:
        if SysRole.objects.filter(role_code=code).exists():
            continue
        org_id = None
        if org_code is not None:
            org = SysOrg.objects.filter(org_code=org_code).first()
            if org is None:
                raise CommandError(f"角色 {code} 绑定的组织 {org_code} 不存在")
            org_id = org.id
        SysRole.objects.create(
            role_code=code,
            role_name=name,
            realm=realm,
            role_type=role_type,
            org_id=org_id,
            data_scope_type=scope_type,
            assignable_level=level,
            is_builtin=True,
            status=1,
            remark=None,
        )
    _assert()


def _assert():
    expected = {r[0] for r in ROLES}
    actual = set(
        SysRole.objects.filter(role_code__in=expected).values_list(
            "role_code", flat=True
        )
    )
    missing = expected - actual
    if missing:
        raise CommandError(f"角色缺失：{sorted(missing)}")
