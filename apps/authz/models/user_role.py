from typing import ClassVar

from django.db import models


class SysUserRole(models.Model):
    """用户角色绑定表，设计 3.7,共 9 个字段。

    grant_scope_key 生成列与 (user_id, role_id, grant_scope_key) 唯一索引
    在 0002_perm_constraints 的 RunSQL 中建立，本模型只建普通列。
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "identity.SysUser",
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="user_roles",
    )
    role = models.ForeignKey(
        "authz.SysRole",
        on_delete=models.CASCADE,
        db_column="role_id",
        related_name="user_roles",
    )
    grant_scope_org_id = models.BigIntegerField(null=True, blank=True)
    granted_by = models.BigIntegerField()
    granted_at = models.DateTimeField()
    expire_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=20, default="MANUAL")
    batch_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "sys_user_role"
        indexes: ClassVar = [
            models.Index(fields=["user"], name="idx_sys_user_role_user"),
        ]
