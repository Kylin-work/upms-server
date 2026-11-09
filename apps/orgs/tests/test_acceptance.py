import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.identity.models import SysUser
from apps.orgs.models import SysOrg


@pytest.mark.django_db
class TestAppendixC:
    """附录 C 验收校验清单 (自动化验证部分)"""

    def test_06_super_admin_constraint(self):
        """第 6 条：超管四字段必须同时为 NULL (物理约束验证)"""
        # 1. 合法超管
        admin = SysUser.objects.create(
            username="t_admin",
            real_name="T",
            password_hash="x",
            is_platform_admin=True,
            org_id=None,
            position_id=None,
            realm=None,
            store_id=None,
            status=1,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        assert admin.is_platform_admin is True

        # 2. 非法超管（带 org_id），应触发 CheckConstraint 报错
        with pytest.raises(IntegrityError), transaction.atomic():
            SysUser.objects.create(
                username="t_bad_admin",
                real_name="T",
                password_hash="x",
                is_platform_admin=True,
                org_id=999,
                status=1,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

    def test_19_placeholder_path(self):
        """第 19 条：库中不允许存在 '__PENDING__' 或空 path"""
        with pytest.raises(IntegrityError), transaction.atomic():
            SysOrg.objects.create(
                org_code="T_ORG",
                org_name="T",
                org_type="DEPT",
                path="__PENDING__",
                level=2,
                status=1,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

    def test_09_region_code_null(self):
        """第 9 条补充：region_code 必须为 NULL"""
        with pytest.raises(IntegrityError), transaction.atomic():
            SysOrg.objects.create(
                org_code="T_ORG2",
                org_name="T",
                org_type="DEPT",
                path="/1/2/",
                level=2,
                region_code="EAST",
                status=1,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )
