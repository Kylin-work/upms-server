import re

from django.contrib.auth.hashers import check_password
from django.utils import timezone

from apps.identity.models import SysUserPasswordHistory


class PasswordPolicyError(Exception):
    """密码策略校验失败."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


def validate_password_strength(password: str) -> None:
    """
    校验密码强度:长度 >= 10,且必须包含大写字母、小写字母、数字。
    """
    if len(password) < 10:
        raise PasswordPolicyError("PASSWORD_TOO_SHORT")
    if not re.search(r"[A-Z]", password):
        raise PasswordPolicyError("PASSWORD_NO_UPPERCASE")
    if not re.search(r"[a-z]", password):
        raise PasswordPolicyError("PASSWORD_NO_LOWERCASE")
    if not re.search(r"\d", password):
        raise PasswordPolicyError("PASSWORD_NO_DIGIT")


def validate_password_history(user_id: int, new_password: str, limit: int = 3) -> None:
    """
    校验新密码是否与最近 limit 次使用的密码重复。
    """
    # 取最近 N 条历史
    histories = SysUserPasswordHistory.objects.filter(user_id=user_id).order_by(
        "-created_at"
    )[:limit]

    for h in histories:
        if check_password(new_password, h.password_hash):
            raise PasswordPolicyError("PASSWORD_RECENTLY_USED")


def record_password_history(user_id: int, old_password_hash: str) -> None:
    """
    将旧密码写入历史表,并清理超出保留数量的旧记录。
    建议保留最近 5 条(大于校验的 3 条,留点余量)。
    """
    now = timezone.now()
    SysUserPasswordHistory.objects.create(
        user_id=user_id,
        password_hash=old_password_hash,
        created_at=now,
    )

    # 清理:保留最近 5 条
    keep_count = 5
    history_ids = list(
        SysUserPasswordHistory.objects.filter(user_id=user_id)
        .order_by("-created_at")
        .values_list("id", flat=True)
    )
    if len(history_ids) > keep_count:
        SysUserPasswordHistory.objects.filter(id__in=history_ids[keep_count:]).delete()
