from ninja import NinjaAPI

from apps.authz.api.grants import router as grants_router
from apps.guard.api.me import router as me_router
from apps.guard.services.exceptions import GuardError
from apps.identity.api.auth import router as auth_router
from apps.orgs.api.stores import router as stores_router

api = NinjaAPI(title="UPMS", version="1.0")
api.add_router("", me_router)
api.add_router("", auth_router)
api.add_router("", stores_router)
api.add_router("", grants_router)


@api.exception_handler(GuardError)
def guard_error_handler(request, exc: GuardError):
    return api.create_response(
        request,
        {"code": exc.code, "detail": exc.detail},
        status=exc.status_code,
    )
