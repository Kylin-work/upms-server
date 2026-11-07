from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.guard.services.perm import perm
from apps.identity.services.user_batch import (
    BatchUserError,
    create_job,
    parse_csv,
    run_job,
)

router = Router(tags=["identity"])


class BatchUserOut(Schema):
    job_no: str
    total_count: int
    success_count: int
    fail_count: int
    status: str


@router.post(
    "/users/batch", response=BatchUserOut, auth=perm("identity.user.batch_create")
)
def batch_create_users(request, file: File[UploadedFile]):
    # 批量开户:解析 CSV -> 创建作业 -> 逐行建用户,失败行隔离
    try:
        content = file.read()
        rows = parse_csv(content)
        job = create_job(content=content, operator_id=request.user.id)
    except BatchUserError as exc:
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
