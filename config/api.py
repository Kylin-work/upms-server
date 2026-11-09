from ninja import NinjaAPI

from apps.audit.api.queries import router as audit_router
from apps.authz.api.batch_grant import router as batch_grant_router
from apps.authz.api.grants import router as grants_router
from apps.authz.api.permission_sets import router as sets_router
from apps.authz.api.resources import router as resources_router
from apps.authz.api.roles import router as roles_router
from apps.guard.api.me import router as me_router
from apps.guard.services.exceptions import GuardError
from apps.identity.api.auth import router as auth_router
from apps.identity.api.sessions import router as sessions_router
from apps.identity.api.users import router as users_router
from apps.orgs.api.orgs import router as orgs_router
from apps.orgs.api.stores import router as stores_router
from apps.orgs.api.tree import router as tree_router
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
api.add_router("", resources_router)
api.add_router("", sets_router)
api.add_router("", sessions_router)
api.add_router("", tree_router)
api.add_router("", orgs_router)


@api.exception_handler(GuardError)
def guard_error_handler(request, exc: GuardError):
    return api.create_response(
        request,
        {"code": exc.code, "detail": exc.detail},
        status=exc.status_code,
    )


# 在路由挂载完成后，自动触发一次资源同步
# 为了避免服务启动时的循环导入报错，把 import 放在函数内部
def _auto_sync_resources():
    import sys

    if "runserver" in sys.argv or "gunicorn" in sys.argv or "uvicorn" in sys.argv:
        try:
            from apps.support.management.commands.sync_resources import auto_sync

            auto_sync()
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("API 资源自动同步失败")


_auto_sync_resources()
