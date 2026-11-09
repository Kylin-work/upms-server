from apps.guard.selectors.filters import apply_data_scope
from apps.orgs.models import SysOrg


def get_org_tree(scope: dict | None) -> list[dict]:
    """查询组织树，套用数据范围过滤."""
    qs = SysOrg.objects.filter(status=1)
    qs = apply_data_scope(qs, scope, org_field="path")

    orgs = list(qs.order_by("sort_no", "id"))
    
    # 建树
    by_id = {o.id: o for o in orgs}
    children_map = {}
    roots = []
    
    for o in orgs:
        parent_id = o.parent_id
        if parent_id is None or parent_id not in by_id:
            # 找不到父节点（可能是因为父节点被数据范围过滤掉了），作为根节点
            roots.append(o)
        else:
            children_map.setdefault(parent_id, []).append(o)

    def build_node(o):
        return {
            "id": o.id,
            "org_code": o.org_code,
            "org_name": o.org_name,
            "org_type": o.org_type,
            "children": [build_node(c) for c in children_map.get(o.id, [])],
        }

    return [build_node(r) for r in roots]
