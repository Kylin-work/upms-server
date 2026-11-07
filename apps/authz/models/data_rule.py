from django.db import models


class SysDataRule(models.Model):
    """行/列级兜底规则表，设计 3.6,共 12 个字段。"""

    id = models.BigAutoField(primary_key=True)
    rule_code = models.CharField(max_length=64, unique=True)
    rule_name = models.CharField(max_length=64)
    rule_type = models.CharField(max_length=10)
    apply_subject_type = models.CharField(max_length=10)
    apply_subject_id = models.BigIntegerField()
    resource_code = models.CharField(max_length=128, null=True, blank=True)
    condition_expr = models.JSONField(null=True, blank=True)
    column_masks = models.JSONField(null=True, blank=True)
    effect = models.CharField(max_length=10, default="RESTRICT")
    priority = models.IntegerField(default=0)
    status = models.SmallIntegerField(default=1)

    class Meta:
        db_table = "sys_data_rule"
