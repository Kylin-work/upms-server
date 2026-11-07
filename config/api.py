from ninja import NinjaAPI

from apps.guard.api.me import router as me_router
from apps.guard.services.exceptions import GuardError

api = NinjaAPI(title="UPMS", version="1.0")
api.add_router("", me_router)


@api.exception_handler(GuardError)
def guard_error_handler(request, exc: GuardError):
    return api.create_response(
        request,
        {"code": exc.code, "detail": exc.detail},
        status=exc.status_code,
    )
