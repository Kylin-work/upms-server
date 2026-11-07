from ninja import Router, Schema
from pydantic import Field

from apps.authz.services.snapshot import load_permission_snapshot
from apps.guard.services.perm import perm

router = Router(tags=["me"])


class UserBrief(Schema):
    id: int
    name: str
    realm: str | None
    org_id: int | None


class MenuNode(Schema):
    code: str
    name: str
    icon: str | None = None
    path: str | None = None
    children: list["MenuNode"] = Field(default_factory=list)


class PermissionsResponse(Schema):
    perm_version: int
    user: UserBrief
    menus: list[MenuNode] = Field(default_factory=list)
    buttons: list[str] = Field(default_factory=list)
    apis: list[str] = Field(default_factory=list)
    data_scopes: dict
    column_masks: dict
    etag: str


class MenusResponse(Schema):
    perm_version: int
    menus: list[MenuNode] = Field(default_factory=list)
    etag: str


class ButtonsResponse(Schema):
    perm_version: int
    buttons: list[str] = Field(default_factory=list)
    etag: str


@router.get(
    "/me/permissions",
    response=PermissionsResponse,
    auth=perm("me.perm.view"),
)
def get_my_permissions(request):
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "user": {
            "id": user.id,
            "name": user.real_name,
            "realm": user.realm,
            "org_id": user.org_id,
        },
        "menus": snapshot["menu_tree"],
        "buttons": snapshot["button_codes"],
        "apis": snapshot["api_codes"],
        "data_scopes": snapshot["data_scopes"],
        "column_masks": snapshot["column_masks"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }


@router.get(
    "/me/menus",
    response=MenusResponse,
    auth=perm("me.perm.view"),
)
def get_my_menus(request):
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "menus": snapshot["menu_tree"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }


@router.get(
    "/me/buttons",
    response=ButtonsResponse,
    auth=perm("me.perm.view"),
)
def get_my_buttons(request):
    user = request.user
    snapshot = load_permission_snapshot(user)
    return {
        "perm_version": snapshot["perm_version"],
        "buttons": snapshot["button_codes"],
        "etag": f'W/"{snapshot["perm_version"]}-{user.id}"',
    }
