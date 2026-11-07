from django.db import migrations


SQL = [
    # 1) 超管四字段 + 非超管 org_id 非空（设计 3.3 完整表达式，两半缺一不可）
    """ALTER TABLE sys_user
         ADD CONSTRAINT chk_user_platform_admin_org
         CHECK (
           (is_platform_admin = TRUE
             AND org_id IS NULL AND position_id IS NULL
             AND realm IS NULL AND store_id IS NULL)
           OR (is_platform_admin = FALSE AND org_id IS NOT NULL)
         )""",

    # 2) 本期不设区域层级
    """ALTER TABLE sys_org ADD CONSTRAINT chk_org_region_null
         CHECK (region_code IS NULL)""",

    # 3) 禁止批量建店占位值残留
    """ALTER TABLE sys_org ADD CONSTRAINT chk_org_path_pending
         CHECK (path <> '__PENDING__' AND path <> '')""",

    # 4) 生成列 + 唯一索引：先把 NULL 归一化成 0，否则 MySQL 唯一索引对 NULL 不去重
    """ALTER TABLE sys_user_role
         ADD COLUMN grant_scope_key BIGINT
           GENERATED ALWAYS AS (IFNULL(grant_scope_org_id, 0)) STORED,
         ADD UNIQUE KEY uk_user_role_scope (user_id, role_id, grant_scope_key)""",

    # 5) 前缀索引
    """CREATE INDEX idx_sys_org_path ON sys_org (path(191))""",

    # 6a) 跨表 realm 一致性：BEFORE INSERT
    """CREATE TRIGGER trg_rps_realm_bi BEFORE INSERT ON sys_role_permission_set
       FOR EACH ROW
       BEGIN
         IF (SELECT realm FROM sys_role WHERE id = NEW.role_id)
            <> (SELECT realm FROM sys_permission_set WHERE id = NEW.set_id) THEN
           SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'REALM_VIOLATION';
         END IF;
       END""",

    # 6b) 跨表 realm 一致性：BEFORE UPDATE
    """CREATE TRIGGER trg_rps_realm_bu BEFORE UPDATE ON sys_role_permission_set
       FOR EACH ROW
       BEGIN
         IF (SELECT realm FROM sys_role WHERE id = NEW.role_id)
            <> (SELECT realm FROM sys_permission_set WHERE id = NEW.set_id) THEN
           SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'REALM_VIOLATION';
         END IF;
       END""",

    # 7) 只读权限集保障：BEFORE INSERT
    """CREATE TRIGGER trg_psi_query_only_bi BEFORE INSERT ON sys_permission_set_item
       FOR EACH ROW
       BEGIN
         IF NEW.set_id = (SELECT id FROM sys_permission_set
                           WHERE set_code = 'ps_hq_store_report_view')
            AND (SELECT op_type FROM sys_resource WHERE id = NEW.resource_id) <> 'QUERY' THEN
           SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'READONLY_SET_VIOLATION';
         END IF;
       END""",
]

REVERSE_SQL = [
    "DROP TRIGGER IF EXISTS trg_psi_query_only_bi",
    "DROP TRIGGER IF EXISTS trg_rps_realm_bu",
    "DROP TRIGGER IF EXISTS trg_rps_realm_bi",
    "DROP INDEX idx_sys_org_path ON sys_org",
    "ALTER TABLE sys_user_role DROP INDEX uk_user_role_scope, DROP COLUMN grant_scope_key",
    "ALTER TABLE sys_org DROP CHECK chk_org_path_pending",
    "ALTER TABLE sys_org DROP CHECK chk_org_region_null",
    "ALTER TABLE sys_user DROP CHECK chk_user_platform_admin_org",
]


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0003_sysorgposition"),
        ("identity", "0002_sysuserposition"),
        ("authz", "0003_sysdatarule_sysdatascoperule_sysroleresourcegrant_and_more"),
    ]

    operations = [migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL)]