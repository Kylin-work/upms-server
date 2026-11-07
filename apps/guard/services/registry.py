from apps.authz.models import SysResource

_registry: dict[str, SysResource] | None = None


def load_registry() -> dict[str, SysResource]:
    global _registry
    if _registry is None:
        _registry = {r.resource_code: r for r in SysResource.objects.filter(status=1)}
    return _registry


def get_resource(resource_code: str) -> SysResource | None:
    return load_registry().get(resource_code)


def invalidate_registry() -> None:
    global _registry
    _registry = None
