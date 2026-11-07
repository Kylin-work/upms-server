from typing import ClassVar

from django.db import models


class SysResource(models.Model):
    """资源表，设计 3.5,共 14 个字段。"""

    id = models.BigAutoField(primary_key=True)
    resource_code = models.CharField(max_length=128, unique=True)
    resource_name = models.CharField(max_length=64)
    res_type = models.CharField(max_length=10)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="parent_id",
        related_name="children",
    )
    op_type = models.CharField(max_length=10)
    realm_scope = models.CharField(max_length=20)
    http_method = models.CharField(max_length=10, null=True, blank=True)
    api_pattern = models.CharField(max_length=255, null=True, blank=True)
    menu_path = models.CharField(max_length=255, null=True, blank=True)
    menu_icon = models.CharField(max_length=64, null=True, blank=True)
    menu_sort = models.IntegerField(default=0)
    is_public = models.BooleanField(default=False)
    status = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "sys_resource"
        indexes: ClassVar = [
            models.Index(
                fields=["res_type", "status"], name="idx_sys_resource_type_status"
            ),
        ]
