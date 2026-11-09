import uuid

from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.guard.services.perm import perm
from apps.orgs.selectors.store import get_store, list_stores
from apps.orgs.services.store import (
    StoreServiceError,
    create_store,
    disable_store,
    update_store,
)
from apps.orgs.services.store_batch import (
    BatchStoreError,
    create_job,
    parse_csv,
    run_job,
)

router = Router(tags=["orgs"])


class StoreOut(Schema):
    id: int
    org_code: str
    org_name: str
    org_type: str
    status: int
    path: str


class StoreCreateIn(Schema):
    org_code: str
    org_name: str
    org_type: str
    parent_code: str = "DEPT_OPS"


class StoreUpdateIn(Schema):
    org_name: str | None = None


class BatchOut(Schema):
    job_no: str
    total_count: int
    success_count: int
    fail_count: int
    status: str


@router.get("/orgs/stores", response=list[StoreOut], auth=perm("org.store.list"))
def list_stores_api(request):
    # 只返回启用门店,再按数据范围过滤
    qs = list_stores(request.ctx_data_scope)
    return list(qs.values("id", "org_code", "org_name", "org_type", "status", "path"))


@router.post("/orgs/stores", response=StoreOut, auth=perm("org.store.create"))
def create_store_api(request, payload: StoreCreateIn):
    # 单条建店:path 回填、岗位实例化、审计写入由服务层完成
    try:
        store = create_store(
            org_code=payload.org_code,
            org_name=payload.org_name,
            org_type=payload.org_type,
            parent_code=payload.parent_code,
            operator_id=request.user.id,
            trace_id=uuid.uuid4().hex,
            request_path=request.path,
            ip=_client_ip(request),
        )
    except StoreServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": store.id,
        "org_code": store.org_code,
        "org_name": store.org_name,
        "org_type": store.org_type,
        "status": store.status,
        "path": store.path,
    }


@router.post("/orgs/stores/batch", response=BatchOut, auth=perm("org.store.create"))
def batch_create_stores(request, file: File[UploadedFile]):
    # 批量建店:解析 CSV -> 创建作业 -> 逐行建店,失败行隔离
    try:
        content = file.read()
        rows = parse_csv(content)
        job = create_job(content=content, operator_id=request.user.id)
    except BatchStoreError as exc:
        # 重复提交返回 409,其余 400
        status = 409 if exc.code.startswith("DUPLICATE_JOB") else 400
        raise HttpError(status, exc.code) from exc
    run_job(job=job, rows=rows, operator_id=request.user.id)
    return {
        "job_no": job.job_no,
        "total_count": job.total_count,
        "success_count": job.success_count,
        "fail_count": job.fail_count,
        "status": job.status,
    }


@router.get("/orgs/stores/{store_id}", response=StoreOut, auth=perm("org.store.list"))
def get_store_api(request, store_id: int):
    # 详情:套数据范围过滤,不在范围内的门店返回 404
    try:
        store = get_store(store_id, request.ctx_data_scope)
    except StoreServiceError as exc:
        raise HttpError(404, exc.code) from exc
    return {
        "id": store.id,
        "org_code": store.org_code,
        "org_name": store.org_name,
        "org_type": store.org_type,
        "status": store.status,
        "path": store.path,
    }


@router.put("/orgs/stores/{store_id}", response=StoreOut, auth=perm("org.store.create"))
def update_store_api(request, store_id: int, payload: StoreUpdateIn):
    # 更新:只允许改 org_name,改 org_code/parent 属于组织移动,不在本接口范围
    try:
        store = update_store(
            store_id=store_id,
            org_name=payload.org_name,
            operator_id=request.user.id,
            trace_id=uuid.uuid4().hex,
            request_path=request.path,
            ip=_client_ip(request),
        )
    except StoreServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": store.id,
        "org_code": store.org_code,
        "org_name": store.org_name,
        "org_type": store.org_type,
        "status": store.status,
        "path": store.path,
    }


@router.delete("/orgs/stores/{store_id}", auth=perm("org.store.create"))
def disable_store_api(request, store_id: int):
    # 停用:软删,status 置 0,不物理删除
    try:
        disable_store(
            store_id=store_id,
            operator_id=request.user.id,
            trace_id=uuid.uuid4().hex,
            request_path=request.path,
            ip=_client_ip(request),
        )
    except StoreServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {"success": True}


def _client_ip(request) -> str | None:
    # 优先取反向代理透传的 X-Forwarded-For,回落到 REMOTE_ADDR
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
