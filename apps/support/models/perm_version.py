from django.db import models


class SysPermVersion(models.Model):
    """权限版本表，设计 3.9,共 3 个字段。

    scope_key 为 VARCHAR(64) 主键(非自增 id),格式 GLOBAL / USER:{id} /
    ROLE:{id} / SET:{id}。无外键，由业务事务以 INSERT ... ON DUPLICATE KEY
    UPDATE version = version + 1 原子递增，是缓存失效的唯一触发源。
    """

    scope_key = models.CharField(max_length=64, primary_key=True)
    version = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "sys_perm_version"
