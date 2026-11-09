from datetime import datetime

from ninja import Router, Schema
from pydantic import Field

from apps.guard.services.exceptions import Forbidden
from apps.guard.services.perm import perm
from apps.support.models import SysBatchJob, SysBatchJobItem

router = Router(tags=["jobs"])


class JobOut(Schema):
    job_no: str = Field(..., description="作业编号")
    job_type: str = Field(
        ..., description="作业类型:BATCH_STORE/BATCH_ACCOUNT/BATCH_GRANT"
    )
    total_count: int = Field(..., description="总行数")
    success_count: int = Field(..., description="成功行数")
    fail_count: int = Field(..., description="失败行数")
    status: str = Field(
        ..., description="作业状态:PENDING/RUNNING/PARTIAL/SUCCESS/FAILED"
    )
    operator_id: int = Field(..., description="提交人ID")
    started_at: datetime | None = Field(None, description="开始时间")
    finished_at: datetime | None = Field(None, description="结束时间")


class JobItemOut(Schema):
    row_no: int = Field(..., description="原始文件中的行号")
    biz_key: str = Field(..., description="业务主键(如门店编码、工号)")
    status: str = Field(..., description="行状态:SUCCESS/FAIL/SKIP")
    error_code: str | None = Field(None, description="错误码(仅失败行有)")
    error_msg: str | None = Field(None, description="错误说明(仅失败行有)")


class ItemsOut(Schema):
    items: list[JobItemOut] = Field(
        default_factory=list, description="失败或跳过的明细行"
    )


@router.get(
    "/jobs/{job_no}",
    response=JobOut,
    auth=perm("platform.job.view"),
    summary="查询作业汇总状态",
)
def get_job(request, job_no: str):
    """
    查询单个批量作业的进度与汇总结果.

    普通用户只能查询自己提交的作业,超管可查全部.
    """
    job = SysBatchJob.objects.filter(job_no=job_no).first()
    if job is None:
        raise Forbidden("JOB_NOT_FOUND")

    # 越权保护:非超管只能看自己的作业
    if not request.user.is_platform_admin and job.operator_id != request.user.id:
        raise Forbidden("JOB_NOT_FOUND")

    return {
        "job_no": job.job_no,
        "job_type": job.job_type,
        "total_count": job.total_count,
        "success_count": job.success_count,
        "fail_count": job.fail_count,
        "status": job.status,
        "operator_id": job.operator_id,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


@router.get(
    "/jobs/{job_no}/items",
    response=ItemsOut,
    auth=perm("platform.job.view"),
    summary="查询作业失败明细",
)
def get_job_items(request, job_no: str):
    """
    查询批量作业的明细列表,通常用于导出失败行重新提交.

    普通用户只能查询自己提交的作业,超管可查全部.
    """
    job = SysBatchJob.objects.filter(job_no=job_no).first()
    if job is None:
        raise Forbidden("JOB_NOT_FOUND")

    # 越权保护:非超管只能看自己的作业
    if not request.user.is_platform_admin and job.operator_id != request.user.id:
        raise Forbidden("JOB_NOT_FOUND")

    items = (
        SysBatchJobItem.objects.filter(job=job)
        .exclude(status="SUCCESS")
        .order_by("row_no")
    )
    return {
        "items": [
            {
                "row_no": it.row_no,
                "biz_key": it.biz_key,
                "status": it.status,
                "error_code": it.error_code,
                "error_msg": it.error_msg,
            }
            for it in items
        ]
    }
