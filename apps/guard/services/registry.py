from django.core.cache import cache

from apps.authz.models import SysResource

REGISTRY_CACHE_KEY = "guard:resource_registry"
REGISTRY_TTL = 3600


def load_registry() -> dict[str, SysResource]:
    # 先查 Redis 缓存,miss 时查库并回写
    cached = cache.get(REGISTRY_CACHE_KEY)
    if cached is not None:
        return cached
    registry = {r.resource_code: r for r in SysResource.objects.filter(status=1)}
    cache.set(REGISTRY_CACHE_KEY, registry, REGISTRY_TTL)
    return registry


def get_resource(resource_code: str) -> SysResource | None:
    return load_registry().get(resource_code)


def invalidate_registry() -> None:
    # 资源变更后调用,所有进程共享同一份缓存
    cache.delete(REGISTRY_CACHE_KEY)
