from django.core.management.base import BaseCommand

from apps.authz.models import SysResource
from apps.guard.services.registry import invalidate_registry


def _extract_resource_code(auth_callbacks) -> str | None:
    """从 ninja 的 auth_callbacks 列表里，通过闭包抠出 perm() 绑定的资源码."""
    for func in auth_callbacks:
        closure = getattr(func, "__closure__", None)
        if not closure:
            continue
        for cell in closure:
            contents = cell.cell_contents
            if isinstance(contents, str) and "." in contents:
                return contents
    return None


class Command(BaseCommand):
    help = "从路由对象自动同步 API 资源到数据库"

    def handle(self, *args, **options):
        from config.api import api

        created_count = 0
        updated_count = 0

        for prefix, router in api._routers:
            for path, path_ops in router.path_operations.items():
                for op in path_ops.operations:
                    resource_code = _extract_resource_code(op.auth_callbacks)
                    if not resource_code:
                        continue

                    method = op.methods[0].upper() if op.methods else "GET"
                    path_str = f"/api/v1{prefix}{path}"

                    resource = SysResource.objects.filter(
                        resource_code=resource_code
                    ).first()
                    if not resource:
                        doc = (op.view_func.__doc__ or "").strip()
                        resource_name = doc.split("\n")[0] if doc else resource_code
                        SysResource.objects.create(
                            resource_code=resource_code,
                            resource_name=resource_name,
                            res_type="API",
                            op_type="QUERY" if method == "GET" else "WRITE",
                            realm_scope="ALL",
                            http_method=method,
                            api_pattern=path_str,
                            is_public=False,
                            status=1,
                        )
                        created_count += 1
                    else:
                        resource.api_pattern = path_str
                        resource.http_method = method
                        resource.save(update_fields=["api_pattern", "http_method"])
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"同步完成: 新建 {created_count} 个资源, 更新 {updated_count} 个资源"
            )
        )
        invalidate_registry()
