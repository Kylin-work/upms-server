from typing import ClassVar

from django.db import models


class SysRole(models.Model):
    """角色表，设计 3.4，共 11 个字段。

    文档 3.4 字段表写 role_code 单列 UNIQUE，关键约束另写 UNIQUE(role_code, realm)，
    二者矛盾；此处按字段表执行（单列唯一），不影响数据正确性。
    """

    id = models.BigAutoField(primary_key=True)
    role_code = models.CharField(max_length=64, unique=True)
    role_name = models.CharField(max_length=64)
    realm = models.CharField(max_length=20)
    role_type = models.CharField(max_length=20)
    org = models.ForeignKey(
        "orgs.SysOrg",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="org_id",
        related_name="roles",
    )
    data_scope_type = models.CharField(max_length=20)
    assignable_level = models.CharField(max_length=20)
    is_builtin = models.BooleanField(default=False)
    status = models.SmallIntegerField(default=1)
    remark = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "sys_role"
        indexes: ClassVar = [
            models.Index(fields=["realm", "status"], name="idx_sys_role_realm_status"),
        ]
