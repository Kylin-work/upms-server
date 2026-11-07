from typing import ClassVar

from django.db import models


class SysUser(models.Model):
    """用户表，设计 3.3，共 17 个字段。

    mobile 本期按普通字符串存储，加密存储与哈希查重方案待定（见设计 3.3
    「手机号加密存储，同时存一份哈希用于查重」），不阻塞表结构落地。
    """

    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64, unique=True)
    employee_no = models.CharField(max_length=32, null=True, blank=True, unique=True)
    real_name = models.CharField(max_length=64)
    mobile = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    email = models.CharField(max_length=128, null=True, blank=True)
    password_hash = models.CharField(max_length=255)
    org = models.ForeignKey(
        "orgs.SysOrg",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="org_id",
        related_name="users",
    )
    position = models.ForeignKey(
        "orgs.SysPosition",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="position_id",
        related_name="users",
    )
    realm = models.CharField(max_length=20, null=True, blank=True)
    store = models.ForeignKey(
        "orgs.SysOrg",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="store_id",
        related_name="store_users",
    )
    is_platform_admin = models.BooleanField()
    status = models.SmallIntegerField(default=1)
    pwd_updated_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "sys_user"
        indexes: ClassVar = [
            models.Index(fields=["org", "status"], name="idx_sys_user_org_status"),
        ]
