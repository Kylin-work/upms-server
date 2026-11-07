from django.db.models import Q

from apps.authz.services.scope import normalize_path


def apply_data_scope(qs, scope, org_field: str = "org_path"):
    if scope is None:
        return qs
    scope_type = scope.get("type")
    if scope_type == "ALL":
        return qs
    if scope_type == "NONE":
        return qs.none()
    if scope_type == "ORG_TREE":
        prefixes = [normalize_path(p) for p in scope.get("path_prefixes", [])]
        exact = [normalize_path(p) for p in scope.get("exact_paths", [])]
        if not prefixes and not exact:
            return qs.none()
        q = Q()
        for prefix in prefixes:
            q |= Q(**{f"{org_field}__startswith": prefix})
        for p in exact:
            q |= Q(**{org_field: p})
        return qs.filter(q)
    if scope_type == "SELF_ONLY":
        return qs.filter(created_by_id=scope["user_id"])
    return qs.none()
