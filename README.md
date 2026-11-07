# UPMS

连锁零售企业统一权限管理系统（UPMS）。

## 本地环境

建库须指定 `utf8mb4_0900_ai_ci`，否则 Django 建表回落到 `utf8mb4_unicode_ci`
（Django 的 `OPTIONS.collation` 不生效）。建库脚本见 `scripts/init_db.sql`。
