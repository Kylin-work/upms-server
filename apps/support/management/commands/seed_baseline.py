from django.core.management.base import BaseCommand

from ._seeders import (
    data_scope_rules,
    orgs,
    permission_sets,
    positions,
    roles,
    super_admin,
)

STEPS = {
    "orgs": orgs.run,
    "positions": positions.run,
    "roles": roles.run,
    "permission_sets": permission_sets.run,
    "data_scope_rules": data_scope_rules.run,
    "super_admin": super_admin.run,
}


class Command(BaseCommand):
    help = "灌入权限基线数据（手册第 2 节）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--step",
            choices=sorted(STEPS),
            required=True,
            help="要执行的步骤",
        )

    def handle(self, *args, **options):
        STEPS[options["step"]]()
