from typing import ClassVar

from django.db import models


class SysPermissionSetItem(models.Model):
    """权限集条目表，设计 3.4,共 5 个字段。"""

    id = models.BigAutoField(primary_key=True)
    set = models.ForeignKey(
        "authz.SysPermissionSet",
        on_delete=models.CASCADE,
        db_column="set_id",
        related_name="items",
    )
    resource = models.ForeignKey(
        "authz.SysResource",
        on_delete=models.CASCADE,
        db_column="resource_id",
        related_name="set_items",
    )
    effect = models.CharField(max_length=10, default="ALLOW")
    granted_at = models.DateTimeField()

    class Meta:
        db_table = "sys_permission_set_item"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["set", "resource"],
                name="uk_set_resource",
            ),
        ]
