from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.authz.models import (
    SysPermissionSet,
    SysPermissionSetItem,
    SysResource,
    SysRole,
)
from apps.orgs.models import SysOrg, SysPosition

HQ = "HQ"
DEPTS = [
    ("DEPT_PUR", "采购部", "PUR"),
    ("DEPT_SALES", "销售部", "SALES"),
    ("DEPT_WHS", "仓储部", "WHS"),
    ("DEPT_FIN", "财务部", "FIN"),
    ("DEPT_IT", "信息部", "IT"),
    ("DEPT_ADM", "行政部", "ADM"),
    ("DEPT_OPS", "运营部", "OPS"),
]

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

# (resource_code, resource_name, res_type, op_type, realm_scope, http_method, api_pattern)
RESOURCES = [
    ("menu.store", "门店管理", "MENU", "QUERY", "ALL", None, None),
    ("menu.store.list", "门店列表", "MENU", "QUERY", "ALL", None, None),
    ("org.store.list", "门店列表接口", "API", "QUERY", "ALL", "GET", "/api/v1/stores"),
    (
        "org.store.create",
        "批量建店接口",
        "API",
        "WRITE",
        "ALL",
        "POST",
        "/api/v1/orgs/stores/batch",
    ),
    (
        "franchise.store.report.query",
        "加盟门店报表查询",
        "API",
        "QUERY",
        "FRANCHISE",
        "GET",
        "/api/v1/franchise/stores/report",
    ),
    ("store.create", "新建门店按钮", "BUTTON", "WRITE", "ALL", None, None),
    ("store.export", "导出门店按钮", "BUTTON", "QUERY", "ALL", None, None),
    ("report.download", "报表下载按钮", "BUTTON", "QUERY", "ALL", None, None),
]

# (set_code, set_name, realm, set_type)
PERMISSION_SETS = [
    ("ps_hq_dept_base", "总部部门基础权限", "HQ", "FUNCTION"),
    ("ps_hq_store_report_view", "总部门店报表只读", "HQ", "FUNCTION"),
    ("ps_hq_ops_manage", "运营部管理权限", "HQ", "FUNCTION"),
    ("ps_direct_store_full", "直营门店全权", "DIRECT", "FUNCTION"),
    ("ps_direct_store_readonly", "直营门店只读", "DIRECT", "FUNCTION"),
    ("ps_franchise_store_admin", "加盟店管理权限", "FRANCHISE", "FUNCTION"),
    ("ps_franchise_store_biz", "加盟店业务权限", "FRANCHISE", "FUNCTION"),
]

# 权限集 → 资源码映射，按手册 2.4「内容要点」与附录 B 推断
SET_ITEMS = {
    "ps_hq_dept_base": ["menu.store", "menu.store.list", "org.store.list"],
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


class Command(BaseCommand):
    help = "灌入权限基线数据（手册第 2 节）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--step",
            choices=["orgs", "positions", "roles", "permission_sets"],
            required=True,
            help="要执行的步骤",
        )

    def handle(self, *args, **options):
        step = options["step"]
        if step == "orgs":
            self.seed_orgs()
        elif step == "positions":
            self.seed_positions()
        elif step == "roles":
            self.seed_roles()
        elif step == "permission_sets":
            self.seed_permission_sets()

    @transaction.atomic
    def seed_orgs(self):
        now = timezone.now()
        hq = SysOrg.objects.filter(org_code=HQ).first()
        if hq is None:
            hq = SysOrg.objects.create(
                parent=None,
                org_code=HQ,
                org_name="总部",
                org_type="HQ",
                path="/",
                level=1,
                manage_owner_type="COMPANY",
                status=1,
                sort_no=0,
                created_at=now,
                updated_at=now,
            )
            hq.path = f"/{hq.id}/"
            hq.save(update_fields=["path"])

        for code, name, dept_code in DEPTS:
            dept = SysOrg.objects.filter(org_code=code).first()
            if dept is None:
                dept = SysOrg.objects.create(
                    parent=hq,
                    org_code=code,
                    org_name=name,
                    org_type="DEPT",
                    path="/",
                    level=2,
                    dept_code=dept_code,
                    manage_owner_type="COMPANY",
                    status=1,
                    sort_no=0,
                    created_at=now,
                    updated_at=now,
                )
                dept.path = f"{hq.path}{dept.id}/"
                dept.save(update_fields=["path"])

        self._assert_orgs()

    @transaction.atomic
    def seed_positions(self):
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
        self._assert_positions()

    @transaction.atomic
    def seed_roles(self):
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
        self._assert_roles()

    @transaction.atomic
    def seed_permission_sets(self):
        for (
            code,
            name,
            res_type,
            op_type,
            realm_scope,
            http_method,
            api_pattern,
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
                    menu_sort=0,
                    is_public=False,
                    status=1,
                )
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
        self._assert_permission_sets()

    def _assert_orgs(self):
        try:
            ops = SysOrg.objects.get(org_code="DEPT_OPS")
        except SysOrg.DoesNotExist as exc:
            raise CommandError("DEPT_OPS 不存在") from exc
        if ops.dept_code != "OPS":
            raise CommandError("DEPT_OPS 的 dept_code 必须为 OPS")
        if SysOrg.objects.filter(region_code__isnull=False).exists():
            raise CommandError("存在 region_code 非空的组织节点")
        if SysOrg.objects.filter(path__in=["", "__PENDING__"]).exists():
            raise CommandError("存在占位或空 path")
        codes = [HQ] + [d[0] for d in DEPTS]
        for org in SysOrg.objects.filter(org_code__in=codes):
            if not org.path.endswith("/"):
                raise CommandError(f"{org.org_code} 的 path 未以 / 结尾")

    def _assert_positions(self):
        expected = {p[0] for p in POSITIONS}
        actual = set(
            SysPosition.objects.filter(position_code__in=expected).values_list(
                "position_code", flat=True
            )
        )
        missing = expected - actual
        if missing:
            raise CommandError(f"岗位缺失：{sorted(missing)}")

    def _assert_roles(self):
        expected = {r[0] for r in ROLES}
        actual = set(
            SysRole.objects.filter(role_code__in=expected).values_list(
                "role_code", flat=True
            )
        )
        missing = expected - actual
        if missing:
            raise CommandError(f"角色缺失：{sorted(missing)}")

    def _assert_permission_sets(self):
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
        # 只读集必须只含 QUERY 资源
        view_set = SysPermissionSet.objects.get(set_code="ps_hq_store_report_view")
        bad = (
            SysPermissionSetItem.objects.filter(set=view_set)
            .exclude(resource__op_type="QUERY")
            .exists()
        )
        if bad:
            raise CommandError("ps_hq_store_report_view 含非 QUERY 资源")
