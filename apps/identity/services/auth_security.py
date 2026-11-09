from django.core.cache import cache

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


def _fail_key(username: str) -> str:
    return f"login:fail:{username}"


def is_locked(username: str) -> bool:
    return (cache.get(_fail_key(username)) or 0) >= MAX_FAILED_ATTEMPTS


def record_failure(username: str) -> int:
    key = _fail_key(username)
    # 如果 key 不存在，先初始化为 0，并设置过期时间
    if cache.add(key, 0, LOCKOUT_SECONDS):
        count = cache.incr(key)
    else:
        count = cache.incr(key)
    return count


def clear_failures(username: str) -> None:
    cache.delete(_fail_key(username))
