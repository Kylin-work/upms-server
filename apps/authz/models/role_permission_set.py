from typing import ClassVar

from django.db import models


class SysRolePermissionSet(models.Model):
    """角色-权限集绑定表，设计 3.4,共 5 个字段。"""

    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(
        "authz.SysRole",
        on_delete=models.CASCADE,
        db_column="role_id",
        related_name="role_sets",
    )
    set = models.ForeignKey(
        "authz.SysPermissionSet",
        on_delete=models.CASCADE,
        db_column="set_id",
        related_name="role_sets",
    )
    effect = models.CharField(max_length=10, default="ALLOW")
    priority = models.IntegerField(default=0)

    class Meta:
        db_table = "sys_role_permission_set"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["role", "set"],
                name="uk_role_set",
            ),
        ]
