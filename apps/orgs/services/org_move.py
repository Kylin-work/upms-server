from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.authz.models import SysRole
from apps.identity.models import SysUser
from apps.orgs.models import SysOrg
from apps.support.models import SysPermVersion


class OrgMoveError(Exception):
    """组织移动异常，携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


@transaction.atomic
def move_org(*, org_id: int, new_parent_id: int) -> SysOrg:
    """移动组织节点，重写子树 path 并递增相关版本号."""
    org = SysOrg.objects.filter(id=org_id).first()
    if not org:
        raise OrgMoveError("ORG_NOT_FOUND")

    new_parent = SysOrg.objects.filter(id=new_parent_id, status=1).first()
    if not new_parent:
        raise OrgMoveError("NEW_PARENT_NOT_FOUND")

    # 校验不能移动到自己或自己的子树下
    if new_parent.path.startswith(org.path) or new_parent.id == org.id:
        raise OrgMoveError("INVALID_MOVE_TARGET")

    # 校验层级合法性
    _validate_org_type(org, new_parent)

    old_path = org.path
    new_path = f"{new_parent.path}{org.id}/"

    # 如果 path 没变，说明位置没变，直接返回
    if old_path == new_path:
        return org

    # 1. 更新节点自身的 parent、level 和 path
    level_offset = new_parent.level + 1 - org.level
    org.parent = new_parent
    org.level = new_parent.level + 1
    org.path = new_path
    org.save(update_fields=["parent", "level", "path"])

    # 2. 查出所有子节点，在 Python 里替换 path 后批量更新
    descendants = list(
        SysOrg.objects.filter(path__startswith=old_path).exclude(id=org.id)
    )
    for child in descendants:
        child.path = child.path.replace(old_path, new_path, 1)
        child.level += level_offset

    if descendants:
        SysOrg.objects.bulk_update(descendants, ["path", "level"])

    # 3. 递增版本号 (GLOBAL, 子树内 USER, 相关 ROLE)
    now = timezone.now()
    _bump_version("GLOBAL", now)

    user_ids = SysUser.objects.filter(
        org__path__startswith=new_path, status=1
    ).values_list("id", flat=True)
    for uid in user_ids:
        _bump_version(f"USER:{uid}", now)

    role_ids = SysRole.objects.filter(status=1).values_list("id", flat=True)
    for rid in role_ids:
        _bump_version(f"ROLE:{rid}", now)

    return org


def _validate_org_type(org: SysOrg, new_parent: SysOrg):
    """校验目标节点是否合法."""
    if org.org_type in ("STORE_DIRECT", "STORE_FRANCHISE"):
        raise OrgMoveError("STORE_CANNOT_BE_MOVED_AS_SUBTREE")

    if org.org_type == "DEPT":
        if new_parent.org_type != "HQ":
            raise OrgMoveError("DEPT_MUST_BE_UNDER_HQ")
    elif org.org_type == "HQ":
        raise OrgMoveError("CANNOT_MOVE_HQ")


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
