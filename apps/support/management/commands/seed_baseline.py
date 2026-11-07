from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.orgs.models import SysOrg

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


class Command(BaseCommand):
    help = "灌入权限基线数据（手册第 2 节）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--step",
            choices=["orgs"],
            required=True,
            help="要执行的步骤",
        )

    def handle(self, *args, **options):
        step = options["step"]
        if step == "orgs":
            self.seed_orgs()

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
