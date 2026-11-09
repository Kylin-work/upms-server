from ninja import NinjaAPI

from apps.audit.api.queries import router as audit_router
from apps.authz.api.batch_grant import router as batch_grant_router
from apps.authz.api.grants import router as grants_router
from apps.authz.api.roles import router as roles_router
from apps.guard.api.me import router as me_router
from apps.guard.services.exceptions import GuardError
from apps.identity.api.auth import router as auth_router
from apps.identity.api.users import router as users_router
from apps.orgs.api.stores import router as stores_router
from apps.support.api.jobs import router as jobs_router

api = NinjaAPI(title="UPMS", version="1.0")
api.add_router("", me_router)
api.add_router("", auth_router)
api.add_router("", stores_router)
api.add_router("", grants_router)
api.add_router("", batch_grant_router)
api.add_router("", users_router)
api.add_router("", audit_router)
api.add_router("", jobs_router)
api.add_router("", roles_router)


@api.exception_handler(GuardError)
def guard_error_handler(request, exc: GuardError):
    return api.create_response(
        request,
        {"code": exc.code, "detail": exc.detail},
        status=exc.status_code,
    )
