from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.guard.services.perm import perm
from apps.orgs.services.org_move import OrgMoveError, move_org

router = Router(tags=["orgs"])


class OrgMoveIn(Schema):
    new_parent_id: int = Field(..., description="目标父节点的组织ID")


@router.put(
    "/orgs/{org_id}/move",
    auth=perm("org.move"),
    summary="移动组织节点",
)
def move_org_api(request, org_id: int, payload: OrgMoveIn):
    """
    移动组织节点到新的父节点下。
    
    这是一个重操作，会重写整个子树的 path，并递增相关用户和角色的版本号。
    """
    try:
        org = move_org(org_id=org_id, new_parent_id=payload.new_parent_id)
    except OrgMoveError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": org.id,
        "org_code": org.org_code,
        "path": org.path,
        "level": org.level,
        "parent_id": org.parent_id,
    }
