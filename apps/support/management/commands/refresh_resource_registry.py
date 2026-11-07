from django.core.management.base import BaseCommand

from apps.guard.services.registry import invalidate_registry


class Command(BaseCommand):
    help = "刷新资源注册表缓存"

    def handle(self, *args, **options):
        invalidate_registry()
        self.stdout.write("resource registry cache invalidated")
