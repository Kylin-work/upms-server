from django.core.cache import caches

from apps.guard.services.exceptions import Unauthorized
from apps.guard.services.jwt_utils import decode_token
from apps.identity.models import SysUser

SESSION_BLACKLIST = caches["session_blacklist"]


def authenticate(request) -> SysUser:
    token = _extract_token(request)
    if not token:
        raise Unauthorized("NO_TOKEN")

    payload = decode_token(token)
    if payload is None:
        raise Unauthorized("TOKEN_INVALID")

    jti = payload.get("jti")
    if jti and SESSION_BLACKLIST.get(f"session:blacklist:{jti}"):
        raise Unauthorized("SESSION_REVOKED")

    user = SysUser.objects.filter(id=int(payload["sub"])).first()
    if user is None or user.status != 1:
        raise Unauthorized("USER_DISABLED")

    request.user = user
    return user


def _extract_token(request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[len("Bearer ") :].strip() or None
