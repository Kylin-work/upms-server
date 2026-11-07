from django.core.management.base import CommandError
from django.db import transaction

from apps.authz.models import SysDataScopeRule, SysRole
from apps.orgs.models import SysOrg

FRANCHISE_REPORT_RESOURCE = "franchise.store.report.query"


@transaction.atomic
def run():
    franchise_ids = list(
        SysOrg.objects.filter(org_type="STORE_FRANCHISE", status=1).values_list(
            "id", flat=True
        )
    )
    hq_roles = SysRole.objects.filter(realm="HQ", status=1)
    for role in hq_roles:
        SysDataScopeRule.objects.get_or_create(
            role=role,
            resource_code=FRANCHISE_REPORT_RESOURCE,
            defaults={
                "scope_type": "ORG_SET",
                "scope_org_ids": franchise_ids,
                "include_children": True,
                "priority": 10,
                "status": 1,
            },
        )
    _assert()


def _assert():
    hq_role_ids = list(
        SysRole.objects.filter(realm="HQ", status=1).values_list("id", flat=True)
    )
    covered = set(
        SysDataScopeRule.objects.filter(
            role_id__in=hq_role_ids,
            resource_code=FRANCHISE_REPORT_RESOURCE,
            status=1,
        ).values_list("role_id", flat=True)
    )
    missing = set(hq_role_ids) - covered
    if missing:
        raise CommandError(f"以下 HQ 角色缺少加盟店报表范围规则：{sorted(missing)}")
