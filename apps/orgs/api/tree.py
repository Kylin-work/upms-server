from ninja import Router, Schema
from pydantic import Field

from apps.guard.services.perm import perm
from apps.orgs.selectors.tree import get_org_tree

router = Router(tags=["orgs"])


class OrgNodeOut(Schema):
    id: int = Field(..., description="组织ID")
    org_code: str = Field(..., description="组织编码")
    org_name: str = Field(..., description="组织名称")
    org_type: str = Field(..., description="组织类型")
    children: list["OrgNodeOut"] = Field(default_factory=list, description="子节点")


@router.get(
    "/orgs/tree",
    response=list[OrgNodeOut],
    auth=perm("org.tree.view"),
    summary="获取组织树",
)
def get_org_tree_api(request):
    """
    返回当前用户数据范围内的组织架构树。
    """
    return get_org_tree(request.ctx_data_scope)
