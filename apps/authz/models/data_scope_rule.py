from django.db import models


class SysDataScopeRule(models.Model):
    """数据范围规则表，设计 3.6,共 10 个字段。"""

    id = models.BigAutoField(primary_key=True)
    role = models.ForeignKey(
        "authz.SysRole",
        on_delete=models.CASCADE,
        db_column="role_id",
        related_name="data_scope_rules",
    )
    resource_code = models.CharField(max_length=128, null=True, blank=True)
    scope_type = models.CharField(max_length=20)
    scope_org_id = models.BigIntegerField(null=True, blank=True)
    scope_org_ids = models.JSONField(null=True, blank=True)
    include_children = models.BooleanField(default=True)
    extra_filter = models.JSONField(null=True, blank=True)
    priority = models.IntegerField(default=0)
    status = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "sys_data_scope_rule"
