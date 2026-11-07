from typing import ClassVar

from django.db import models


class SysOrgPosition(models.Model):
    """组织岗位实例表，设计 3.2,共 5 个字段。"""

    id = models.BigAutoField(primary_key=True)
    org = models.ForeignKey(
        "orgs.SysOrg",
        on_delete=models.CASCADE,
        db_column="org_id",
        related_name="org_position_links",
    )
    position = models.ForeignKey(
        "orgs.SysPosition",
        on_delete=models.CASCADE,
        db_column="position_id",
        related_name="org_positions",
    )
    headcount = models.IntegerField(default=0)
    status = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "sys_org_position"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["org", "position"],
                name="uk_org_position",
            ),
        ]
