from django.core.cache import cache

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _fail_key(username: str) -> str:
    return f"login:fail:{username}"


def is_locked(username: str) -> bool:
    return (cache.get(_fail_key(username)) or 0) >= MAX_FAILED_ATTEMPTS


def record_failure(username: str) -> int:
    key = _fail_key(username)
    if cache.add(key, 0, LOCKOUT_SECONDS):
        count = cache.incr(key)
    else:
        count = cache.incr(key)
    return count


def clear_failures(username: str) -> None:
    cache.delete(_fail_key(username))


def _force_logout_key(user_id: int) -> str:
    return f"user:force_logout_at:{user_id}"


def force_logout(user_id: int) -> None:
    """强制下线指定用户的所有设备,记录当前时间戳."""
    import time

    # 存当前时间戳,有效期设为 Refresh Token 的最大有效期(7天),防止内存泄漏
    cache.set(_force_logout_key(user_id), int(time.time()), 7 * 24 * 3600)


def is_force_logged_out(user_id: int, token_iat: int) -> bool:
    """检查 Token 的签发时间是否早于该用户被强制下线的时间."""
    force_at = cache.get(_force_logout_key(user_id))
    if force_at is None:
        return False
    return token_iat < force_at


def clear_force_logout(user_id: int) -> None:
    cache.delete(_force_logout_key(user_id))
