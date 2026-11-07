from django.db import migrations


SQL = [
    """CREATE TRIGGER trg_psi_query_only_bu BEFORE UPDATE ON sys_permission_set_item
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
    "DROP TRIGGER IF EXISTS trg_psi_query_only_bu",
]


class Migration(migrations.Migration):
    dependencies = [
        ("authz", "0004_perm_constraints"),
    ]

    operations = [migrations.RunSQL(sql=SQL, reverse_sql=REVERSE_SQL)]