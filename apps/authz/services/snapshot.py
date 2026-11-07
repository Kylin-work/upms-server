import json

from django.core.cache import cache
from django.utils import timezone

from apps.authz.models import (
    SysPermissionSetItem,
    SysRolePermissionSet,
    SysRoleResourceGrant,
    SysUserRole,
)
from apps.authz.services.scope import build_data_scopes
from apps.support.models import SysPermVersion

SNAPSHOT_TTL = 1800
SNAPSHOT_PREFIX = "perm:snapshot"


def load_permission_snapshot(user) -> dict:
    version = current_perm_version(user.id)
    key = build_cache_key(user.id, version)
    raw = cache.get(key)
    if raw is not None:
        return json.loads(raw)
    snapshot = build_snapshot_from_db(user, version)
    cache.set(key, json.dumps(snapshot), SNAPSHOT_TTL)
    return snapshot


def build_cache_key(user_id: int, version: int) -> str:
    return f"{SNAPSHOT_PREFIX}:{user_id}:{version}"


def current_perm_version(user_id: int) -> int:
    global_v = _read_version("GLOBAL")
    user_v = _read_version(f"USER:{user_id}")
    return global_v * 1_000_000 + user_v


def _read_version(scope_key: str) -> int:
    row = SysPermVersion.objects.filter(scope_key=scope_key).first()
    return row.version if row else 0


def build_snapshot_from_db(user, version: int) -> dict:
    role_ids = _effective_role_ids(user.id)
    api_codes, button_codes = _collect_codes(role_ids)
    data_scopes = build_data_scopes(user)
    menu_codes = _collect_menu_codes(role_ids)
    return {
        "user_id": user.id,
        "perm_version": version,
        "realm": user.realm,
        "api_codes": sorted(api_codes),
        "button_codes": sorted(button_codes),
        "data_scopes": data_scopes,
        "column_masks": {},
        "menu_tree": _build_menu_tree(menu_codes),
    }


def _collect_menu_codes(role_ids: list[int]) -> set[str]:
    codes: set[str] = set()
    deny: set[str] = set()
    set_ids = SysRolePermissionSet.objects.filter(
        role_id__in=role_ids,
    ).values_list("set_id", flat=True)
    for item in SysPermissionSetItem.objects.filter(set_id__in=set_ids).select_related(
        "resource"
    ):
        if item.resource.res_type != "MENU":
            continue
        if item.effect == "DENY":
            deny.add(item.resource.resource_code)
        else:
            codes.add(item.resource.resource_code)
    return codes - deny


def _build_menu_tree(menu_codes: set[str]) -> list[dict]:
    from apps.authz.models import SysResource

    if not menu_codes:
        return []
    resources = list(
        SysResource.objects.filter(
            resource_code__in=menu_codes, res_type="MENU", status=1
        )
    )
    children_map: dict[str | None, list] = {}
    for r in resources:
        parent_code = None
        if r.parent_id is not None:
            parent = SysResource.objects.filter(id=r.parent_id).first()
            parent_code = parent.resource_code if parent else None
        children_map.setdefault(parent_code, []).append(r)

    def build_node(r) -> dict:
        node = {
            "code": r.resource_code,
            "name": r.resource_name,
            "icon": r.menu_icon,
            "path": r.menu_path,
            "children": [],
        }
        for child in sorted(
            children_map.get(r.resource_code, []), key=lambda x: (x.menu_sort, x.id)
        ):
            node["children"].append(build_node(child))
        return node

    roots = []
    for r in sorted(children_map.get(None, []), key=lambda x: (x.menu_sort, x.id)):
        node = build_node(r)
        if node["children"] or node["path"]:
            roots.append(node)
    return roots


def _effective_role_ids(user_id: int) -> list[int]:
    now = timezone.now()
    ids = []
    for b in SysUserRole.objects.filter(user_id=user_id, role__status=1):
        if b.expire_at is not None and b.expire_at <= now:
            continue
        ids.append(b.role_id)
    return ids


def _collect_codes(role_ids: list[int]) -> tuple[set[str], set[str]]:
    api_allow: set[str] = set()
    button_allow: set[str] = set()
    deny: set[str] = set()

    set_ids = SysRolePermissionSet.objects.filter(
        role_id__in=role_ids,
    ).values_list("set_id", flat=True)
    for item in SysPermissionSetItem.objects.filter(set_id__in=set_ids).select_related(
        "resource"
    ):
        if item.effect == "DENY":
            deny.add(item.resource.resource_code)
        elif item.resource.res_type == "API":
            api_allow.add(item.resource.resource_code)
        elif item.resource.res_type == "BUTTON":
            button_allow.add(item.resource.resource_code)

    for grant in SysRoleResourceGrant.objects.filter(
        role_id__in=role_ids
    ).select_related("resource"):
        if grant.effect == "DENY":
            deny.add(grant.resource.resource_code)
        elif grant.resource.res_type == "API":
            api_allow.add(grant.resource.resource_code)
        elif grant.resource.res_type == "BUTTON":
            button_allow.add(grant.resource.resource_code)

    return api_allow - deny, button_allow - deny
