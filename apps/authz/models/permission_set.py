from django.db import models


class SysPermissionSet(models.Model):
    """权限集表，设计 3.4,共 7 个字段。"""

    id = models.BigAutoField(primary_key=True)
    set_code = models.CharField(max_length=64, unique=True)
    set_name = models.CharField(max_length=64)
    realm = models.CharField(max_length=20)
    set_type = models.CharField(max_length=20)
    version = models.IntegerField(default=1)
    status = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "sys_permission_set"
