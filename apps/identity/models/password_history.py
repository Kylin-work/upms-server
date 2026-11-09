from django.db import models


class SysUserPasswordHistory(models.Model):
    """用户密码历史表，用于防止重复使用最近 N 次密码。"""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "identity.SysUser",
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="password_histories",
    )
    password_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "sys_user_password_history"
        indexes = [  # noqa: RUF012
            models.Index(fields=["user", "-created_at"], name="idx_user_pwd_history"),
        ]
