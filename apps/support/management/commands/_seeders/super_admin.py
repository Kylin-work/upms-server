from django.contrib.auth.hashers import make_password
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from apps.identity.models import SysUser

SUPER_ADMIN_USERNAME = "admin"
SUPER_ADMIN_REAL_NAME = "超级管理员"
SUPER_ADMIN_INITIAL_PASSWORD = "Admin@123456"


@transaction.atomic
def run():
    now = timezone.now()
    user = SysUser.objects.filter(username=SUPER_ADMIN_USERNAME).first()
    if user is None:
        SysUser.objects.create(
            username=SUPER_ADMIN_USERNAME,
            real_name=SUPER_ADMIN_REAL_NAME,
            password_hash=make_password(SUPER_ADMIN_INITIAL_PASSWORD),
            is_platform_admin=True,
            org_id=None,
            position_id=None,
            realm=None,
            store_id=None,
            status=1,
            pwd_updated_at=now,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
    _assert()


def _assert():
    try:
        user = SysUser.objects.get(username=SUPER_ADMIN_USERNAME)
    except SysUser.DoesNotExist as exc:
        raise CommandError("超管账号不存在") from exc
    if not user.is_platform_admin:
        raise CommandError("超管账号 is_platform_admin 不为 TRUE")
    if any([user.org_id, user.position_id, user.realm, user.store_id]):
        raise CommandError(
            "超管账号的 org_id/position_id/realm/store_id 必须同时为 NULL"
        )
