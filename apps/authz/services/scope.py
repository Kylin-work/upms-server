from django.utils import timezone

from apps.authz.models import SysDataScopeRule, SysRole, SysUserRole
from apps.orgs.models import SysOrg

WILDCARD = "*"


def build_data_scopes(user) -> dict[str, dict]:
    """按设计 4.5 第 1–7 步推导用户数据范围,返回 5.8.1 的 data_scopes."""
    if user.is_platform_admin:
        return {WILDCARD: {"type": "ALL"}}

    roles = _load_effective_roles(user.id)
    if not roles:
        return {WILDCARD: {"type": "NONE"}}

    per_resource: dict[str, list[dict]] = {}
    for role in roles:
        rules = list(
            SysDataScopeRule.objects.filter(role=role, status=1).order_by("-priority")
        )
        for rule in rules:
            if rule.resource_code is None:
                continue
            per_resource.setdefault(rule.resource_code, []).append(
                _rule_to_scope(rule, user)
            )
        default_scope = _role_default_scope(role, user)
        if default_scope is not None:
            per_resource.setdefault(WILDCARD, []).append(default_scope)

    result: dict[str, dict] = {}
    for resource_code, scopes in per_resource.items():
        merged = _merge_scopes(scopes)
        if merged is not None:
            result[resource_code] = merged

    if WILDCARD not in result:
        result[WILDCARD] = {"type": "NONE"}
    return result


def _load_effective_roles(user_id: int) -> list[SysRole]:
    now = timezone.now()
    bindings = SysUserRole.objects.filter(
        user_id=user_id,
        role__status=1,
    ).select_related("role")
    role_ids = [b.role_id for b in bindings if b.expire_at is None or b.expire_at > now]
    if not role_ids:
        return []
    return list(SysRole.objects.filter(id__in=role_ids, status=1))


def _role_default_scope(role: SysRole, user) -> dict | None:
    scope_type = role.data_scope_type
    if scope_type == "ALL":
        return {"type": "ALL"}
    if scope_type == "NONE":
        return {"type": "NONE"}
    if scope_type == "SELF_ONLY":
        return {"type": "SELF_ONLY", "user_id": user.id}
    if scope_type == "ORG_SUBTREE":
        org_id = role.org_id or user.org_id
        org = SysOrg.objects.filter(id=org_id).first()
        if org is None:
            return None
        return {"type": "ORG_TREE", "path_prefixes": [normalize_path(org.path)]}
    if scope_type == "ORG_SELF":
        org = SysOrg.objects.filter(id=user.org_id).first()
        if org is None:
            return None
        return {"type": "ORG_TREE", "path_prefixes": [normalize_path(org.path)]}
    return None


def _rule_to_scope(rule: SysDataScopeRule, user) -> dict:
    scope_type = rule.scope_type
    if scope_type == "ALL":
        return {"type": "ALL"}
    if scope_type == "ORG_SUBTREE":
        org = SysOrg.objects.filter(id=rule.scope_org_id).first()
        if org is None:
            return {"type": "NONE"}
        return {"type": "ORG_TREE", "path_prefixes": [normalize_path(org.path)]}
    if scope_type == "ORG_SELF":
        org = SysOrg.objects.filter(id=user.org_id).first()
        if org is None:
            return {"type": "NONE"}
        return {"type": "ORG_TREE", "path_prefixes": [normalize_path(org.path)]}
    if scope_type == "ORG_SET":
        ids = rule.scope_org_ids or []
        orgs = list(SysOrg.objects.filter(id__in=ids, status=1))
        if not orgs:
            return {"type": "NONE"}
        if rule.include_children:
            return {
                "type": "ORG_TREE",
                "path_prefixes": sorted({normalize_path(o.path) for o in orgs}),
            }
        return {
            "type": "ORG_TREE",
            "exact_paths": sorted({normalize_path(o.path) for o in orgs}),
        }
    if scope_type == "SELF_ONLY":
        return {"type": "SELF_ONLY", "user_id": user.id}
    return {"type": "NONE"}


def _merge_scopes(scopes: list[dict]) -> dict | None:
    if not scopes:
        return None
    for s in scopes:
        if s["type"] == "ALL":
            return {"type": "ALL"}
    prefixes: set[str] = set()
    exact: set[str] = set()
    self_only_user_id = None
    for s in scopes:
        if s["type"] == "ORG_TREE":
            prefixes.update(s.get("path_prefixes", []))
            exact.update(s.get("exact_paths", []))
        elif s["type"] == "SELF_ONLY":
            self_only_user_id = s["user_id"]
    if prefixes or exact:
        result = {"type": "ORG_TREE"}
        if prefixes:
            result["path_prefixes"] = sorted(prefixes)
        if exact:
            result["exact_paths"] = sorted(exact)
        return result
    if self_only_user_id is not None:
        return {"type": "SELF_ONLY", "user_id": self_only_user_id}
    return {"type": "NONE"}


def normalize_path(path: str) -> str:
    if not path.endswith("/"):
        return path + "/"
    return path
