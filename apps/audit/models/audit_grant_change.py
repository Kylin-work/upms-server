from django.db import models


class SysAuditGrantChange(models.Model):
    """授权变更日志表，设计 3.8,共 12 个字段。"""

    id = models.BigAutoField(primary_key=True)
    trace_id = models.CharField(max_length=64)
    operator_id = models.BigIntegerField()
    change_type = models.CharField(max_length=32)
    target_type = models.CharField(max_length=32)
    target_id = models.BigIntegerField()
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    diff_summary = models.CharField(max_length=512, null=True, blank=True)
    reason = models.CharField(max_length=255)
    batch_id = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "sys_audit_grant_change"
