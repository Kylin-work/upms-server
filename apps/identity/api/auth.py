from django.contrib.auth.hashers import check_password
from django.utils import timezone
from ninja import Router, Schema

from apps.guard.services.exceptions import Unauthorized
from apps.guard.services.jwt_utils import encode_access_token
from apps.identity.models import SysUser

router = Router(tags=["auth"])


class LoginIn(Schema):
    username: str
    password: str


class LoginOut(Schema):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: int
    real_name: str


@router.post("/auth/login", response=LoginOut)
def login(request, payload: LoginIn):
    user = SysUser.objects.filter(username=payload.username).first()
    if user is None or not check_password(payload.password, user.password_hash):
        raise Unauthorized("BAD_CREDENTIAL")
    if user.status != 1:
        raise Unauthorized("USER_DISABLED")

    token = encode_access_token(user.id)
    now = timezone.now()
    SysUser.objects.filter(id=user.id).update(last_login_at=now, updated_at=now)

    from django.conf import settings

    return {
        "access_token": token,
        "expires_in": settings.JWT_ACCESS_EXPIRE_SECONDS,
        "user_id": user.id,
        "real_name": user.real_name,
    }
