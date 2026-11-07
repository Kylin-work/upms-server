from typing import ClassVar

from django.db import models


class SysBatchJob(models.Model):
    """批量作业主表，设计 3.9,共 12 个字段。"""

    id = models.BigAutoField(primary_key=True)
    job_no = models.CharField(max_length=64, unique=True)
    job_type = models.CharField(max_length=32)
    idempotency_key = models.CharField(max_length=128, unique=True)
    total_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20)
    payload_ref = models.CharField(max_length=255, null=True, blank=True)
    operator_id = models.BigIntegerField()
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sys_batch_job"
        indexes: ClassVar = [
            models.Index(fields=["status"], name="idx_sys_batch_job_status"),
        ]
