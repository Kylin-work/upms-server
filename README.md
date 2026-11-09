UPMS 连锁零售企业统一权限管理系统 (后端)

本项目是基于 Django 5.2 + Django Ninja 构建的后端服务。实现了多组织架构下的 RBAC 权限控制、数据范围隔离、审计日志追踪以及异步批处理能力。

技术栈：
Python 3.12+
Django 5.2 LTS
Django Ninja (API)
MySQL 8.0+
Redis 7.x+
Celery (异步任务)

一键启动 (开发环境)

方式一：使用 Docker Compose（推荐）
确保本机已安装 Docker 和 Docker Compose。

1. 启动基础设施（MySQL 和 Redis）
docker-compose up -d db redis

2. 安装依赖并运行迁移
uv sync
uv run python manage.py migrate

3. 灌入基础权限数据（组织、角色、权限等）
for s in orgs positions roles permission_sets role_sets data_scope_rules super_admin; do uv run python manage.py seed_baseline --step "$s"; done

4. 启动 Django API
uv run python manage.py runserver

5. 启动 Celery Worker (新开一个终端)
uv run celery -A config worker --loglevel=info

启动后访问：
API 文档 (Swagger UI): http://127.0.0.1:8000/api/v1/docs
默认超管账号: admin / Admin@123456

方式二：手动连接本机服务
如果本机已有 MySQL 和 Redis，请修改 config/settings/local.py 中的 DATABASES 和 REDIS_URL，然后执行上述第 2 步到第 5 步。

本地联调与测试：
uv run ruff check .
uv run pytest

核心 API 说明：
/auth/login: 登录，签发 Access 和 Refresh Token
/me/permissions: 获取当前用户的完整权限快照（菜单、按钮、数据范围）
/orgs/stores: 门店管理（支持数据范围过滤）
/authz/roles/{id}/grants: 角色授权（权限集绑定）
/jobs/{job_no}: 查询异步批处理任务的进度和失败明细

架构说明：
组织域：采用物化路径 (path) 存储树结构，实现高效的子树数据范围过滤。
权限模型：三层鉴权（身份认证 -> 功能权限 -> 数据范围），并引入了组织域 (Realm) 隔离直营和加盟。
工程化：统一的 JSON 响应格式、全局异常拦截、Trace ID 日志追踪、IP 限流、CORS 以及 Celery 异步批处理。
