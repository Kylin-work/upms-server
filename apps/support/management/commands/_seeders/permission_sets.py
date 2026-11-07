from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.authz.models import SysPermissionSet, SysPermissionSetItem, SysResource
from apps.guard.services.registry import invalidate_registry
from apps.support.models import SysPermVersion

# (resource_code, resource_name, res_type, op_type, realm_scope, http_method, api_pattern, menu_path, is_public, parent_code)
RESOURCES = [
    (
        "me.perm.view",
        "当前用户权限查询",
        "API",
        "QUERY",
        "ALL",
        "GET",
        "/api/v1/me/permissions",
        None,
        True,
        None,
    ),
    (
        "menu.store",
        "门店管理",
        "MENU",
        "QUERY",
        "ALL",
        None,
        None,
        "/store",
        False,
        None,
    ),
    (
        "menu.store.list",
        "门店列表",
        "MENU",
        "QUERY",
        "ALL",
        None,
        None,
        "/store/list",
        False,
        "menu.store",
    ),
    (
        "org.store.list",
        "门店列表接口",
        "API",
        "QUERY",
        "ALL",
        "GET",
        "/api/v1/stores",
        None,
        False,
        None,
    ),
    (
        "org.store.create",
        "批量建店接口",
        "API",
        "WRITE",
        "ALL",
        "POST",
        "/api/v1/orgs/stores/batch",
        None,
        False,
        None,
    ),
    (
        "franchise.store.report.query",
        "加盟门店报表查询",
        "API",
        "QUERY",
        "FRANCHISE",
        "GET",
        "/api/v1/franchise/stores/report",
        None,
        False,
        None,
    ),
    (
        "authz.role.grant",
        "角色授权接口",
        "API",
        "ADMIN",
        "ALL",
        "POST",
        "/api/v1/authz/roles/{role_id}/grants",
        None,
        False,
        None,
    ),
    (
        "identity.user.batch_create",
        "批量开户接口",
        "API",
        "WRITE",
        "ALL",
        "POST",
        "/api/v1/users/batch",
        None,
        False,
        None,
    ),
    (
        "audit.operation.query",
        "操作日志查询接口",
        "API",
        "QUERY",
        "ALL",
        "GET",
        "/api/v1/audit/operations",
        None,
        False,
        None,
    ),
    (
        "audit.grant.query",
        "授权变更日志查询接口",
        "API",
        "QUERY",
        "ALL",
        "GET",
        "/api/v1/audit/grant-changes",
        None,
        False,
        None,
    ),
    (
        "store.create",
        "新建门店按钮",
        "BUTTON",
        "WRITE",
        "ALL",
        None,
        None,
        None,
        False,
        None,
    ),
    (
        "store.export",
        "导出门店按钮",
        "BUTTON",
        "QUERY",
        "ALL",
        None,
        None,
        None,
        False,
        None,
    ),
    (
        "report.download",
        "报表下载按钮",
        "BUTTON",
        "QUERY",
        "ALL",
        None,
        None,
        None,
        False,
        None,
    ),
]

PERMISSION_SETS = [
    ("ps_hq_dept_base", "总部部门基础权限", "HQ", "FUNCTION"),
    ("ps_hq_store_report_view", "总部门店报表只读", "HQ", "FUNCTION"),
    ("ps_hq_ops_manage", "运营部管理权限", "HQ", "FUNCTION"),
    ("ps_direct_store_full", "直营门店全权", "DIRECT", "FUNCTION"),
    ("ps_direct_store_readonly", "直营门店只读", "DIRECT", "FUNCTION"),
    ("ps_franchise_store_admin", "加盟店管理权限", "FRANCHISE", "FUNCTION"),
    ("ps_franchise_store_biz", "加盟店业务权限", "FRANCHISE", "FUNCTION"),
]

SET_ITEMS = {
    "ps_hq_dept_base": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "authz.role.grant",
        "identity.user.batch_create",
        "audit.operation.query",
        "audit.grant.query",
    ],
    "ps_hq_store_report_view": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "franchise.store.report.query",
        "store.export",
        "report.download",
    ],
    "ps_hq_ops_manage": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "org.store.create",
        "franchise.store.report.query",
        "authz.role.grant",
        "store.create",
        "store.export",
        "report.download",
    ],
    "ps_direct_store_full": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "org.store.create",
        "store.create",
        "store.export",
    ],
    "ps_direct_store_readonly": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "store.export",
    ],
    "ps_franchise_store_admin": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "franchise.store.report.query",
        "store.export",
        "report.download",
    ],
    "ps_franchise_store_biz": [
        "menu.store",
        "menu.store.list",
        "org.store.list",
        "franchise.store.report.query",
        "store.export",
    ],
}


@transaction.atomic
def run():
    for (
        code,
        name,
        res_type,
        op_type,
        realm_scope,
        http_method,
        api_pattern,
        menu_path,
        is_public,
        _,
    ) in RESOURCES:
        if not SysResource.objects.filter(resource_code=code).exists():
            SysResource.objects.create(
                resource_code=code,
                resource_name=name,
                res_type=res_type,
                op_type=op_type,
                realm_scope=realm_scope,
                http_method=http_method,
                api_pattern=api_pattern,
                menu_path=menu_path,
                menu_sort=0,
                is_public=is_public,
                status=1,
            )
    for code, _, _, _, _, _, _, menu_path, _, _ in RESOURCES:
        if menu_path is None:
            continue
        SysResource.objects.filter(resource_code=code).update(menu_path=menu_path)
    for code, _, _, _, _, _, _, _, _, parent_code in RESOURCES:
        if parent_code is None:
            continue
        parent = SysResource.objects.get(resource_code=parent_code)
        SysResource.objects.filter(resource_code=code).update(parent=parent)
    for code, name, realm, set_type in PERMISSION_SETS:
        if not SysPermissionSet.objects.filter(set_code=code).exists():
            SysPermissionSet.objects.create(
                set_code=code,
                set_name=name,
                realm=realm,
                set_type=set_type,
                version=1,
                status=1,
            )
    now = timezone.now()
    for set_code, resource_codes in SET_ITEMS.items():
        pset = SysPermissionSet.objects.get(set_code=set_code)
        for rc in resource_codes:
            resource = SysResource.objects.get(resource_code=rc)
            SysPermissionSetItem.objects.get_or_create(
                set=pset,
                resource=resource,
                defaults={"effect": "ALLOW", "granted_at": now},
            )
    _assert()
    _bump_global_version()
    invalidate_registry()


def _assert():
    expected_res = {r[0] for r in RESOURCES}
    actual_res = set(
        SysResource.objects.filter(resource_code__in=expected_res).values_list(
            "resource_code", flat=True
        )
    )
    missing_res = expected_res - actual_res
    if missing_res:
        raise CommandError(f"资源缺失：{sorted(missing_res)}")
    expected_sets = {s[0] for s in PERMISSION_SETS}
    actual_sets = set(
        SysPermissionSet.objects.filter(set_code__in=expected_sets).values_list(
            "set_code", flat=True
        )
    )
    missing_sets = expected_sets - actual_sets
    if missing_sets:
        raise CommandError(f"权限集缺失：{sorted(missing_sets)}")
    view_set = SysPermissionSet.objects.get(set_code="ps_hq_store_report_view")
    bad = (
        SysPermissionSetItem.objects.filter(set=view_set)
        .exclude(resource__op_type="QUERY")
        .exists()
    )
    if bad:
        raise CommandError("ps_hq_store_report_view 含非 QUERY 资源")


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
