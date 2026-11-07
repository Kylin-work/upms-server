from typing import ClassVar

from django.db import models


class SysOrg(models.Model):
    """组织表，设计 3.2,共 16 个字段。"""

    id = models.BigAutoField(primary_key=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="parent_id",
        related_name="children",
    )
    org_code = models.CharField(max_length=32, unique=True)
    org_name = models.CharField(max_length=128)
    org_type = models.CharField(max_length=20)
    path = models.CharField(max_length=255)
    level = models.SmallIntegerField()
    dept_code = models.CharField(max_length=32, null=True, blank=True)
    store_type = models.CharField(max_length=10, null=True, blank=True)
    manage_owner_type = models.CharField(max_length=20, null=True, blank=True)
    franchise_owner_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    region_code = models.CharField(max_length=32, null=True, blank=True)
    status = models.SmallIntegerField(default=1)
    sort_no = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "sys_org"
        indexes: ClassVar = [
            models.Index(fields=["org_type", "status"], name="idx_sys_org_type_status"),
        ]
