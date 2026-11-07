from typing import ClassVar

from django.db import models


class SysAuditOperation(models.Model):
    """操作日志表，设计 3.8,共 17 个字段。"""

    id = models.BigAutoField(primary_key=True)
    trace_id = models.CharField(max_length=64)
    user_id = models.BigIntegerField(null=True, blank=True)
    username = models.CharField(max_length=64)
    module = models.CharField(max_length=32)
    resource_code = models.CharField(max_length=128)
    http_method = models.CharField(max_length=10)
    request_path = models.CharField(max_length=255)
    params_digest = models.CharField(max_length=512, null=True, blank=True)
    target_type = models.CharField(max_length=32, null=True, blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)
    target_org_id = models.BigIntegerField(null=True, blank=True)
    result = models.CharField(max_length=10)
    error_code = models.CharField(max_length=32, null=True, blank=True)
    cost_ms = models.IntegerField(null=True, blank=True)
    ip = models.CharField(max_length=45, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "sys_audit_operation"
        indexes: ClassVar = [
            models.Index(
                fields=["user_id", "created_at"], name="idx_sys_audit_op_user_time"
            ),
        ]
