from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import caches
from django.utils import timezone
from ninja import Router, Schema

from apps.guard.services.exceptions import Unauthorized
from apps.guard.services.jwt_utils import decode_token, encode_access_token
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


class LogoutOut(Schema):
    success: bool = True


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

    return {
        "access_token": token,
        "expires_in": settings.JWT_ACCESS_EXPIRE_SECONDS,
        "user_id": user.id,
        "real_name": user.real_name,
    }


@router.post("/auth/logout", response=LogoutOut)
def logout(request):
    token = _extract_bearer(request)
    if not token:
        raise Unauthorized("NO_TOKEN")
    payload = decode_token(token)
    if payload is None:
        raise Unauthorized("TOKEN_INVALID")
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        ttl = max(int(exp - timezone.now().timestamp()), 1)

        caches["session_blacklist"].set(f"session:blacklist:{jti}", 1, ttl)
    return {"success": True}


def _extract_bearer(request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[len("Bearer ") :].strip() or None
