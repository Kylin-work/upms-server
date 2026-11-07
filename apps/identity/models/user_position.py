from typing import ClassVar

from django.db import models


class SysUserPosition(models.Model):
    """用户兼职岗位表（预留），设计 3.3，共 5 个字段。

    本期一人一岗，仅写入主岗一条记录（is_primary=True）。
    唯一约束取 (user_id, org_id, position_id) 防重复兼职；
    不对 (user_id, is_primary) 加唯一约束，以免限制未来一人多岗。
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "identity.SysUser",
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="user_positions",
    )
    org = models.ForeignKey(
        "orgs.SysOrg",
        on_delete=models.CASCADE,
        db_column="org_id",
        related_name="user_positions",
    )
    position = models.ForeignKey(
        "orgs.SysPosition",
        on_delete=models.CASCADE,
        db_column="position_id",
        related_name="user_positions",
    )
    is_primary = models.BooleanField()

    class Meta:
        db_table = "sys_user_position"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["user", "org", "position"],
                name="uk_user_position",
            ),
        ]
