from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from pydantic import Field

from apps.guard.services.perm import perm
from apps.identity.services.user import (
    UserServiceError,
    create_user,
    disable_user,
    get_user_detail,
    update_user,
)
from apps.identity.services.user_batch import (
    BatchUserError,
    create_job,
    parse_csv,
    run_job,
)

router = Router(tags=["identity"])


class BatchUserOut(Schema):
    job_no: str = Field(..., description="作业编号")
    total_count: int = Field(..., description="总行数")
    success_count: int = Field(..., description="成功行数")
    fail_count: int = Field(..., description="失败行数")
    status: str = Field(..., description="作业状态")


class UserOut(Schema):
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="登录名")
    real_name: str = Field(..., description="真实姓名")
    org_code: str | None = Field(None, description="所属组织编码")
    position_code: str | None = Field(None, description="岗位编码")
    realm: str | None = Field(None, description="所属域")
    status: int = Field(..., description="状态: 1在职, 0停用")


class UserCreateIn(Schema):
    username: str = Field(..., description="登录名(建议用工号)")
    real_name: str = Field(..., description="真实姓名")
    org_code: str = Field(..., description="所属组织编码")
    position_code: str = Field(..., description="岗位编码")
    mobile: str | None = Field(None, description="手机号")
    email: str | None = Field(None, description="邮箱")
    role_codes: list[str] | None = Field(
        None, description="角色编码列表,不传则用岗位默认角色"
    )


class UserUpdateIn(Schema):
    real_name: str | None = Field(None, description="真实姓名")
    mobile: str | None = Field(None, description="手机号")
    email: str | None = Field(None, description="邮箱")


@router.post(
    "/users/batch",
    response=BatchUserOut,
    auth=perm("identity.user.batch_create"),
    summary="批量开户",
)
def batch_create_users(request, file: File[UploadedFile]):
    """批量开户:解析 CSV -> 创建作业 -> 逐行建用户,失败行隔离."""
    try:
        content = file.read()
        rows = parse_csv(content)
        job = create_job(content=content, operator_id=request.user.id)
    except BatchUserError as exc:
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


@router.post(
    "/users", response=UserOut, auth=perm("identity.user.create"), summary="创建用户"
)
def create_user_api(request, payload: UserCreateIn):
    """创建单个用户,自动绑定岗位与角色."""
    try:
        user = create_user(
            username=payload.username,
            real_name=payload.real_name,
            org_code=payload.org_code,
            position_code=payload.position_code,
            mobile=payload.mobile,
            email=payload.email,
            role_codes=payload.role_codes,
            operator_id=request.user.id,
        )
    except UserServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "org_code": user.org.org_code if user.org else None,
        "position_code": user.position.position_code if user.position else None,
        "realm": user.realm,
        "status": user.status,
    }


@router.get(
    "/users/{user_id}",
    response=UserOut,
    auth=perm("identity.user.view"),
    summary="获取用户详情",
)
def get_user_api(request, user_id: int):
    """根据 ID 查询用户详情,包含数据范围越权校验."""
    try:
        user = get_user_detail(user_id, request.ctx_data_scope)
    except UserServiceError as exc:
        raise HttpError(404, exc.code) from exc
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "org_code": user.org.org_code if user.org else None,
        "position_code": user.position.position_code if user.position else None,
        "realm": user.realm,
        "status": user.status,
    }


@router.put(
    "/users/{user_id}",
    response=UserOut,
    auth=perm("identity.user.update"),
    summary="更新用户",
)
def update_user_api(request, user_id: int, payload: UserUpdateIn):
    """更新用户基础信息."""
    try:
        # 先做越权校验
        get_user_detail(user_id, request.ctx_data_scope)

        user = update_user(
            user_id=user_id,
            real_name=payload.real_name,
            mobile=payload.mobile,
            email=payload.email,
        )
    except UserServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "org_code": user.org.org_code if user.org else None,
        "position_code": user.position.position_code if user.position else None,
        "realm": user.realm,
        "status": user.status,
    }


@router.delete(
    "/users/{user_id}", auth=perm("identity.user.disable"), summary="停用用户"
)
def disable_user_api(request, user_id: int):
    """停用指定用户(软删)."""
    try:
        get_user_detail(user_id, request.ctx_data_scope)
        disable_user(user_id=user_id)
    except UserServiceError as exc:
        raise HttpError(400, exc.code) from exc
    return {"success": True}
