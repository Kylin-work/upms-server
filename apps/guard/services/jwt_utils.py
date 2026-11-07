import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings


def new_jti() -> str:
    return uuid.uuid4().hex


def encode_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "jti": new_jti(),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.JWT_ACCESS_EXPIRE_SECONDS)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError:
        return None
