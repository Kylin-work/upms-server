import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings


def new_jti() -> str:
    return uuid.uuid4().hex


def encode_access_token(user_id: int) -> str:
    """签发 Access Token,默认有效期 2 小时."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "jti": new_jti(),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.JWT_ACCESS_EXPIRE_SECONDS)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def encode_refresh_token(user_id: int) -> str:
    """签发 Refresh Token,默认有效期 7 天."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "jti": new_jti(),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.JWT_REFRESH_EXPIRE_SECONDS)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict | None:
    """解析 Token,并校验 type 字段防止 Access 和 Refresh 混用."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.PyJWTError:
        return None
