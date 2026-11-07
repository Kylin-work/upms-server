from django.db import models


class SysPosition(models.Model):
    """岗位定义表，设计 3.2,共 7 个字段。"""

    id = models.BigAutoField(primary_key=True)
    position_code = models.CharField(max_length=32, unique=True)
    position_name = models.CharField(max_length=64)
    org_type_scope = models.CharField(max_length=50)
    is_management = models.BooleanField()
    default_role_codes = models.JSONField(null=True, blank=True)
    status = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "sys_position"
