from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import caches
from django.utils import timezone
from ninja import Router, Schema
from pydantic import Field

from apps.guard.services.exceptions import Unauthorized
from apps.guard.services.jwt_utils import (
    decode_token,
    encode_access_token,
    encode_refresh_token,
)
from apps.identity.models import SysUser

router = Router(tags=["auth"])

SESSION_BLACKLIST = caches["session_blacklist"]


class LoginIn(Schema):
    username: str = Field(..., description="登录名或工号")
    password: str = Field(..., description="密码")


class LoginOut(Schema):
    access_token: str = Field(..., description="访问令牌,有效期2小时")
    refresh_token: str = Field(..., description="刷新令牌,有效期7天")
    token_type: str = Field("Bearer", description="令牌类型")
    expires_in: int = Field(..., description="Access Token 过期时间(秒)")
    user_id: int = Field(..., description="用户ID")
    real_name: str = Field(..., description="真实姓名")


class RefreshIn(Schema):
    refresh_token: str = Field(..., description="刷新令牌")


class RefreshOut(Schema):
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field("Bearer", description="令牌类型")
    expires_in: int = Field(..., description="Access Token 过期时间(秒)")


class LogoutOut(Schema):
    success: bool = Field(True, description="是否成功登出")


@router.post("/auth/login", response=LoginOut, summary="用户登录")
def login(request, payload: LoginIn):
    """校验账号密码，签发 Access Token 和 Refresh Token。"""
    user = SysUser.objects.filter(username=payload.username).first()
    if user is None or not check_password(payload.password, user.password_hash):
        raise Unauthorized("BAD_CREDENTIAL")
    if user.status != 1:
        raise Unauthorized("USER_DISABLED")

    access_token = encode_access_token(user.id)
    refresh_token = encode_refresh_token(user.id)
    now = timezone.now()
    SysUser.objects.filter(id=user.id).update(last_login_at=now, updated_at=now)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.JWT_ACCESS_EXPIRE_SECONDS,
        "user_id": user.id,
        "real_name": user.real_name,
    }


@router.post("/auth/refresh", response=RefreshOut, summary="刷新Token")
def refresh(request, payload: RefreshIn):
    """使用 Refresh Token 换取新的 Access Token。"""
    # 解析并校验类型，必须是 refresh
    data = decode_token(payload.refresh_token, expected_type="refresh")
    if data is None:
        raise Unauthorized("TOKEN_INVALID")

    # 检查该 refresh token 是否已被登出（列入黑名单）
    jti = data.get("jti")
    if jti and SESSION_BLACKLIST.get(f"session:blacklist:{jti}"):
        raise Unauthorized("SESSION_REVOKED")

    user_id = int(data["sub"])
    user = SysUser.objects.filter(id=user_id).first()
    if user is None or user.status != 1:
        raise Unauthorized("USER_DISABLED")

    # 签发新的 Access Token
    access_token = encode_access_token(user.id)
    return {
        "access_token": access_token,
        "expires_in": settings.JWT_ACCESS_EXPIRE_SECONDS,
    }


@router.post("/auth/logout", response=LogoutOut, summary="用户登出")
def logout(request):
    """将当前 Token 的 jti 写入 Redis 黑名单，使其立即失效。"""
    token = _extract_bearer(request)
    if not token:
        raise Unauthorized("NO_TOKEN")
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise Unauthorized("TOKEN_INVALID")
    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        ttl = max(int(exp - timezone.now().timestamp()), 1)
        SESSION_BLACKLIST.set(f"session:blacklist:{jti}", 1, ttl)
    return {"success": True}


def _extract_bearer(request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[len("Bearer ") :].strip() or None
