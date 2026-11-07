import uuid
from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.audit.services import log_grant_change
from apps.authz.models import (
    SysPermissionSet,
    SysPermissionSetItem,
    SysResource,
    SysRole,
    SysRolePermissionSet,
    SysRoleResourceGrant,
    SysUserRole,
)
from apps.authz.services.snapshot import load_permission_snapshot
from apps.support.models import SysPermVersion


class GrantError(Exception):
    """授权失败,携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


@dataclass
class GrantResult:
    role_id: int
    added_sets: list[str]
    removed_sets: list[str]
    added_resources: list[str]
    removed_resources: list[str]


def can_grant(operator, target_role: SysRole, resource_codes: list[str]) -> bool:
    """设计 5.3 的授权边界校验,超管短路."""
    if operator.is_platform_admin:
        return True
    if target_role.assignable_level not in _operator_levels(operator):
        return False
    if target_role.realm != operator.realm:
        return False
    owned = _owned_resource_codes(operator)
    return all(code in owned for code in resource_codes)


def _operator_levels(operator) -> set[str]:
    # 操作者的可授予层级来自其绑定角色的 assignable_level
    role_ids = SysUserRole.objects.filter(
        user=operator,
        role__status=1,
    ).values_list("role_id", flat=True)
    return set(
        SysRole.objects.filter(id__in=role_ids, status=1).values_list(
            "assignable_level", flat=True
        )
    )


def _owned_resource_codes(operator) -> set[str]:
    # 操作者已拥有的资源码,含 API、按钮、菜单三类
    snapshot = load_permission_snapshot(operator)
    owned = set(snapshot["api_codes"]) | set(snapshot["button_codes"])
    owned |= _collect_menu_codes(snapshot["menu_tree"])
    return owned


def _collect_menu_codes(menu_tree: list[dict]) -> set[str]:
    # 递归收集菜单树里的所有 resource_code
    codes: set[str] = set()

    def walk(nodes):
        for node in nodes:
            codes.add(node["code"])
            walk(node.get("children", []))

    walk(menu_tree)
    return codes


@transaction.atomic
def grant_role(
    *,
    role_id: int,
    set_codes: list[str],
    resource_codes: list[str],
    reason: str,
    operator,
    trace_id: str | None = None,
) -> GrantResult:
    """设计 4.4 的角色授权,含差集计算、审计、版本号递增."""
    role = SysRole.objects.filter(id=role_id).first()
    if role is None:
        raise GrantError("ROLE_NOT_FOUND")

    sets = list(SysPermissionSet.objects.filter(set_code__in=set_codes))
    if len(sets) != len(set_codes):
        raise GrantError("SET_NOT_FOUND")
    for s in sets:
        if s.realm != role.realm:
            raise GrantError("REALM_VIOLATION")

    resources = list(SysResource.objects.filter(resource_code__in=resource_codes))
    if len(resources) != len(resource_codes):
        raise GrantError("RESOURCE_NOT_FOUND")

    # 权限集展开成资源码,与直授资源码合并后统一做授权边界校验
    set_resource_codes = list(
        SysPermissionSetItem.objects.filter(set__in=sets).values_list(
            "resource__resource_code", flat=True
        )
    )
    all_codes = set_resource_codes + [r.resource_code for r in resources]
    if not can_grant(operator, role, all_codes):
        raise GrantError("GRANT_EXCEED_AUTHORITY")

    current_sets = set(
        SysRolePermissionSet.objects.filter(role=role).values_list("set_id", flat=True)
    )
    current_resources = set(
        SysRoleResourceGrant.objects.filter(role=role).values_list(
            "resource_id", flat=True
        )
    )
    target_sets = {s.id for s in sets}
    target_resources = {r.id for r in resources}

    added_set_ids = target_sets - current_sets
    removed_set_ids = current_sets - target_sets
    added_resource_ids = target_resources - current_resources
    removed_resource_ids = current_resources - target_resources

    before = {
        "sets": sorted(
            SysPermissionSet.objects.filter(id__in=current_sets).values_list(
                "set_code", flat=True
            )
        ),
        "resources": sorted(
            SysResource.objects.filter(id__in=current_resources).values_list(
                "resource_code", flat=True
            )
        ),
    }
    after = {
        "sets": sorted(s.set_code for s in sets),
        "resources": sorted(r.resource_code for r in resources),
    }

    now = timezone.now()
    for set_id in added_set_ids:
        SysRolePermissionSet.objects.get_or_create(
            role=role,
            set_id=set_id,
            defaults={"effect": "ALLOW", "priority": 0},
        )
    for set_id in removed_set_ids:
        SysRolePermissionSet.objects.filter(role=role, set_id=set_id).delete()
    for resource_id in added_resource_ids:
        SysRoleResourceGrant.objects.get_or_create(
            role=role,
            resource_id=resource_id,
            defaults={"effect": "ALLOW", "granted_by": operator.id, "granted_at": now},
        )
    for resource_id in removed_resource_ids:
        SysRoleResourceGrant.objects.filter(role=role, resource_id=resource_id).delete()

    _bump_version("GLOBAL", now)
    _bump_version(f"ROLE:{role.id}", now)
    log_grant_change(
        trace_id=trace_id or uuid.uuid4().hex,
        operator_id=operator.id,
        change_type="GRANT",
        target_type="ROLE",
        target_id=role.id,
        before_snapshot=before,
        after_snapshot=after,
        diff_summary=(
            f"+{len(added_set_ids)}sets/-{len(removed_set_ids)}sets/"
            f"+{len(added_resource_ids)}res/-{len(removed_resource_ids)}res"
        ),
        reason=reason,
    )

    return GrantResult(
        role_id=role.id,
        added_sets=[s.set_code for s in sets if s.id in added_set_ids],
        removed_sets=list(
            SysPermissionSet.objects.filter(id__in=removed_set_ids).values_list(
                "set_code", flat=True
            )
        ),
        added_resources=[
            r.resource_code for r in resources if r.id in added_resource_ids
        ],
        removed_resources=list(
            SysResource.objects.filter(id__in=removed_resource_ids).values_list(
                "resource_code", flat=True
            )
        ),
    )


def _bump_version(scope_key: str, now) -> None:
    _, created = SysPermVersion.objects.get_or_create(
        scope_key=scope_key,
        defaults={"version": 1, "updated_at": now},
    )
    if not created:
        SysPermVersion.objects.filter(scope_key=scope_key).update(
            version=F("version") + 1,
            updated_at=now,
        )
