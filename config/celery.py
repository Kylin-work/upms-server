import os

from celery import Celery

# 设置 Django settings 模块
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("upms")

# 从 Django 的 settings 中读取以 CELERY_ 开头的配置
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现所有 app 下的 tasks.py 文件
app.autodiscover_tasks()
