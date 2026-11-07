import csv
import hashlib
import io
import uuid

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.authz.models import SysRole, SysUserRole
from apps.identity.models import SysUser, SysUserPosition
from apps.orgs.models import SysOrg, SysPosition
from apps.support.models import SysBatchJob, SysBatchJobItem

DEFAULT_INITIAL_PASSWORD = "Init@123456"


class BatchUserError(Exception):
    """批量开户失败,携带错误码."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail or code
        super().__init__(self.detail)


REQUIRED_COLUMNS = ["employee_no", "real_name", "org_code", "position_code"]


def parse_csv(content: bytes) -> list[dict]:
    """解析 CSV,首行表头,校验必需列."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise BatchUserError("CSV_EMPTY")
    missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
    if missing:
        raise BatchUserError(f"CSV_MISSING_COLUMNS:{sorted(missing)}")
    return list(reader)


def create_job(*, content: bytes, operator_id: int) -> SysBatchJob:
    """以文件摘要作幂等键,重复提交拒绝."""
    key = hashlib.sha256(content).hexdigest()
    existing = SysBatchJob.objects.filter(idempotency_key=key).first()
    if existing is not None:
        raise BatchUserError(f"DUPLICATE_JOB:{existing.job_no}")
    return SysBatchJob.objects.create(
        job_no=uuid.uuid4().hex,
        job_type="BATCH_ACCOUNT",
        idempotency_key=key,
        total_count=0,
        success_count=0,
        fail_count=0,
        status="PENDING",
        operator_id=operator_id,
        started_at=timezone.now(),
    )


def run_job(*, job: SysBatchJob, rows: list[dict], operator_id: int) -> SysBatchJob:
    """逐行开户,单行失败不影响整批."""
    job.total_count = len(rows)
    job.status = "RUNNING"
    job.save(update_fields=["total_count", "status"])

    success = 0
    fail = 0
    for idx, row in enumerate(rows, start=1):
        biz_key = row.get("employee_no", "")
        try:
            _create_one(row, operator_id=operator_id)
            SysBatchJobItem.objects.create(
                job=job,
                row_no=idx,
                biz_key=biz_key,
                status="SUCCESS",
                result_ref={"employee_no": biz_key},
            )
            success += 1
        except BatchUserError as exc:
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
    """单行开户:校验 realm 一致性、建用户、绑岗位、绑角色."""
    employee_no = row["employee_no"].strip()
    if SysUser.objects.filter(employee_no=employee_no).exists():
        raise BatchUserError("EMPLOYEE_NO_DUPLICATE")
    if SysUser.objects.filter(username=employee_no).exists():
        raise BatchUserError("USERNAME_DUPLICATE")

    org = SysOrg.objects.filter(org_code=row["org_code"].strip(), status=1).first()
    if org is None:
        raise BatchUserError("ORG_NOT_FOUND")
    position = SysPosition.objects.filter(
        position_code=row["position_code"].strip(),
        status=1,
    ).first()
    if position is None:
        raise BatchUserError("POSITION_NOT_FOUND")
    if not _position_fits_org(position, org):
        raise BatchUserError("POSITION_ORG_MISMATCH")

    role_codes = _parse_role_codes(row.get("role_codes", ""))
    if role_codes:
        roles = list(SysRole.objects.filter(role_code__in=role_codes, status=1))
        if len(roles) != len(role_codes):
            raise BatchUserError("ROLE_NOT_FOUND")
    else:
        roles = _roles_from_position(position, org)

    _check_realm(org, roles)

    now = timezone.now()
    user = SysUser.objects.create(
        username=employee_no,
        employee_no=employee_no,
        real_name=row["real_name"].strip(),
        mobile=(row.get("mobile") or "").strip() or None,
        password_hash=make_password(DEFAULT_INITIAL_PASSWORD),
        org=org,
        position=position,
        realm=_realm_of_org(org),
        store=org if org.org_type in ("STORE_DIRECT", "STORE_FRANCHISE") else None,
        is_platform_admin=False,
        status=1,
        pwd_updated_at=now,
        created_at=now,
        updated_at=now,
    )
    SysUserPosition.objects.create(
        user=user,
        org=org,
        position=position,
        is_primary=True,
    )
    for role in roles:
        SysUserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={
                "granted_by": operator_id,
                "granted_at": now,
                "source": "BATCH",
            },
        )


def _position_fits_org(position: SysPosition, org: SysOrg) -> bool:
    # 岗位的 org_type_scope 是逗号分隔的适用组织类型
    scopes = {s.strip() for s in position.org_type_scope.split(",") if s.strip()}
    return org.org_type in scopes


def _realm_of_org(org: SysOrg) -> str:
    if org.org_type == "STORE_DIRECT":
        return "DIRECT"
    if org.org_type == "STORE_FRANCHISE":
        return "FRANCHISE"
    return "HQ"


def _check_realm(org: SysOrg, roles: list[SysRole]) -> None:
    # 组织 realm 与所有待授角色的 realm 必须一致
    org_realm = _realm_of_org(org)
    for role in roles:
        if role.realm != org_realm:
            raise BatchUserError("REALM_MISMATCH")


def _parse_role_codes(raw: str) -> list[str]:
    if not raw:
        return []
    return [c.strip() for c in raw.split(";") if c.strip()]


def _roles_from_position(position: SysPosition, org: SysOrg) -> list[SysRole]:
    """role_codes 为空时,按岗位 default_role_codes 选,按 org realm 二选一."""
    codes = position.default_role_codes or []
    if not codes:
        return []
    org_realm = _realm_of_org(org)
    matched = list(
        SysRole.objects.filter(role_code__in=codes, realm=org_realm, status=1)
    )
    return matched
