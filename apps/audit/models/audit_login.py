from typing import ClassVar

from django.db import models


class SysAuditLogin(models.Model):
    """登录日志表，设计 3.8,共 9 个字段。"""

    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=64)
    login_type = models.CharField(max_length=20)
    login_result = models.CharField(max_length=10)
    fail_reason = models.CharField(max_length=64, null=True, blank=True)
    ip = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "sys_audit_login"
        indexes: ClassVar = [
            models.Index(
                fields=["user_id", "created_at"], name="idx_sys_audit_login_user_time"
            ),
        ]
