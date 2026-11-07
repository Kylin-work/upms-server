from typing import ClassVar

from django.db import models


class SysBatchJobItem(models.Model):
    """批量作业明细表，设计 3.9,共 8 个字段。"""

    id = models.BigAutoField(primary_key=True)
    job = models.ForeignKey(
        "support.SysBatchJob",
        on_delete=models.CASCADE,
        db_column="job_id",
        related_name="items",
    )
    row_no = models.IntegerField()
    biz_key = models.CharField(max_length=128)
    status = models.CharField(max_length=10)
    error_code = models.CharField(max_length=32, null=True, blank=True)
    error_msg = models.CharField(max_length=255, null=True, blank=True)
    result_ref = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "sys_batch_job_item"
        indexes: ClassVar = [
            models.Index(fields=["job"], name="idx_sys_batch_job_item_job"),
        ]
