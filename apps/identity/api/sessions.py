from ninja import Router
from ninja.errors import HttpError

from apps.guard.services.perm import perm
from apps.identity.models import SysUser
from apps.identity.services.auth_security import force_logout

router = Router(tags=["identity"])


@router.post(
    "/users/{user_id}/kick", auth=perm("identity.user.kick"), summary="强制下线用户"
)
def kick_user(request, user_id: int):
    """强制指定用户下线。"""
    user = SysUser.objects.filter(id=user_id).first()
    if not user:
        raise HttpError(404, "USER_NOT_FOUND")

    force_logout(user_id)
    return {"success": True}
