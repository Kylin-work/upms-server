from celery import shared_task

from apps.orgs.services.store_batch import run_job
from apps.support.models import SysBatchJob


@shared_task
def run_store_batch_job(job_id: int, rows: list[dict], operator_id: int):
    """异步执行批量建店任务."""
    job = SysBatchJob.objects.filter(id=job_id).first()
    if not job:
        return "JOB_NOT_FOUND"

    run_job(job=job, rows=rows, operator_id=operator_id)
    return job.status
