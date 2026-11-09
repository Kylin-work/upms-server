import csv
import hashlib
import io
import uuid

from django.db import transaction
from django.utils import timezone

from apps.orgs.services.store import StoreServiceError, create_store
from apps.support.models import SysBatchJob, SysBatchJobItem


class BatchStoreError(Exception):
    """批量建店失败,携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


REQUIRED_COLUMNS = ["store_code", "store_name", "store_type", "parent_code"]


def parse_csv(content: bytes) -> list[dict]:
    """解析 CSV 内容,返回行字典列表.首行必须是表头."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise BatchStoreError("CSV_EMPTY")
    missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
    if missing:
        raise BatchStoreError(f"CSV_MISSING_COLUMNS:{sorted(missing)}")
    return list(reader)


def create_job(
    *,
    content: bytes,
    operator_id: int,
    job_type: str = "BATCH_STORE",
) -> SysBatchJob:
    """计算文件摘要作为幂等键,创建作业主记录."""
    idempotency_key = hashlib.sha256(content).hexdigest()
    existing = SysBatchJob.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        raise BatchStoreError(f"DUPLICATE_JOB:{existing.job_no}")
    job = SysBatchJob.objects.create(
        job_no=uuid.uuid4().hex,
        job_type=job_type,
        idempotency_key=idempotency_key,
        total_count=0,
        success_count=0,
        fail_count=0,
        status="PENDING",
        operator_id=operator_id,
        started_at=timezone.now(),
    )
    return job


def run_job(*, job: SysBatchJob, rows: list[dict], operator_id: int) -> SysBatchJob:
    """逐行建店,每行独立事务,失败不回滚整批."""
    job.total_count = len(rows)
    job.status = "RUNNING"
    job.save(update_fields=["total_count", "status"])

    success = 0
    fail = 0
    for idx, row in enumerate(rows, start=1):
        biz_key = row.get("store_code", "")
        try:
            _create_one(row, operator_id=operator_id)
            SysBatchJobItem.objects.create(
                job=job,
                row_no=idx,
                biz_key=biz_key,
                status="SUCCESS",
                result_ref={"store_code": biz_key},
            )
            success += 1
        except StoreServiceError as exc:
            SysBatchJobItem.objects.create(
                job=job,
                row_no=idx,
                biz_key=biz_key,
                status="FAIL",
                error_code=exc.code,
                error_msg=exc.detail,
            )
            fail += 1
        except Exception as exc:  # noqa: BLE001  单行意外异常不中断整批
            SysBatchJobItem.objects.create(
                job=job,
                row_no=idx,
                biz_key=biz_key,
                status="FAIL",
                error_code="UNEXPECTED",
                error_msg=str(exc)[:255],
            )
            fail += 1

    job.success_count = success
    job.fail_count = fail
    job.status = "SUCCESS" if fail == 0 else "PARTIAL"
    job.finished_at = timezone.now()
    job.save(update_fields=["success_count", "fail_count", "status", "finished_at"])
    return job


@transaction.atomic
def _create_one(row: dict, *, operator_id: int):
    """单行建店,复用单条 CRUD 的服务."""
    create_store(
        org_code=row["store_code"],
        org_name=row["store_name"],
        org_type=_map_store_type(row["store_type"]),
        parent_code=row["parent_code"],
        operator_id=operator_id,
        request_path="/api/v1/orgs/stores/batch",
    )


def _map_store_type(value: str) -> str:
    mapping = {"DIRECT": "STORE_DIRECT", "FRANCHISE": "STORE_FRANCHISE"}
    if value not in mapping:
        raise StoreServiceError("INVALID_STORE_TYPE")
    return mapping[value]
