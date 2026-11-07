from typing import ClassVar

from django.db import models


class SysRoleResourceGrant(models.Model):
    """角色资源直授表，设计 3.7,共 6 个字段。"""

    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(
        "authz.SysRole",
        on_delete=models.CASCADE,
        db_column="role_id",
        related_name="resource_grants",
    )
    resource = models.ForeignKey(
        "authz.SysResource",
        on_delete=models.CASCADE,
        db_column="resource_id",
        related_name="role_grants",
    )
    effect = models.CharField(max_length=10)
    granted_by = models.BigIntegerField()
    granted_at = models.DateTimeField()

    class Meta:
        db_table = "sys_role_resource_grant"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["role", "resource"],
                name="uk_role_resource_grant",
            ),
        ]
