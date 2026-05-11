"""redesign_archive_tables

档案数据模型 v3 重设计：
  - repo_catalog: org_mode → catalog_type (案卷目录|卷内目录|一文一件), 新增 volume_archive_id
  - repo_archive: 重建为 PARTITION BY RANGE(ND) 分区表，删除 parent_id/level/MLH/AJH/JH/storage 字段
  - repo_archive_staging: 新建临时库（非分区，draft/pending_review/rejected 状态）
  - repo_archive_attachment: 新建原文附件表

Revision ID: f9a3c81d2e45
Revises: b3e7f2a1c9d4
Create Date: 2026-04-26 10:00:00.000000

WARNING: upgrade() 会 DROP TABLE repo_archive CASCADE，现有数据将丢失。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f9a3c81d2e45"
down_revision: Union[str, Sequence[str], None] = "b3e7f2a1c9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 分区年度范围
_PARTITION_START = 1990
_PARTITION_END = 2041  # 创建到 2040 年分区


def upgrade() -> None:
    # ── 1. 改造 repo_catalog ──────────────────────────────────────────────────
    op.drop_column("repo_catalog", "org_mode")

    op.add_column(
        "repo_catalog",
        sa.Column(
            "catalog_type", sa.String(20), nullable=False,
            server_default="一文一件",
            comment="目录类型: 案卷目录 | 卷内目录 | 一文一件",
        ),
    )
    op.add_column(
        "repo_catalog",
        sa.Column(
            "volume_archive_id", sa.UUID(), nullable=True,
            comment="卷内目录专用：1:1 关联的案卷暂存记录 ID（无 FK 约束）",
        ),
    )
    op.create_index(
        "ix_repo_catalog_volume_archive_id", "repo_catalog", ["volume_archive_id"]
    )

    # ── 2. 删除旧 repo_archive（CASCADE 清理依赖的 FK） ────────────────────────
    op.execute("DROP TABLE IF EXISTS repo_archive CASCADE")

    # ── 3. 创建分区表 repo_archive ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE repo_archive (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            "ND"        INTEGER     NOT NULL,
            fonds_id    UUID        NOT NULL,
            catalog_id  UUID        NOT NULL,
            category_id UUID        NOT NULL,
            "DH"        VARCHAR(100),
            "QZH"       VARCHAR(50)  NOT NULL,
            "TM"        VARCHAR(512) NOT NULL,
            "RZZ"       VARCHAR(200),
            "WJRQ"      VARCHAR(20),
            "YS"        INTEGER,
            "MJ"        VARCHAR(20)  NOT NULL DEFAULT 'public',
            "BGQX"      VARCHAR(20)  NOT NULL DEFAULT 'permanent',
            status      VARCHAR(30)  NOT NULL DEFAULT 'archived',
            ext_fields  JSONB,
            embedding_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            es_synced_at     VARCHAR(30),
            tenant_id   UUID,
            create_time TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_time TIMESTAMPTZ NOT NULL DEFAULT now(),
            create_by   UUID,
            is_deleted  BOOLEAN     NOT NULL DEFAULT false,
            CONSTRAINT repo_archive_pkey PRIMARY KEY (id, "ND"),
            CONSTRAINT repo_archive_fonds_id_fkey
                FOREIGN KEY (fonds_id) REFERENCES repo_fonds(id) ON DELETE CASCADE,
            CONSTRAINT repo_archive_catalog_id_fkey
                FOREIGN KEY (catalog_id) REFERENCES repo_catalog(id) ON DELETE CASCADE,
            CONSTRAINT repo_archive_category_id_fkey
                FOREIGN KEY (category_id) REFERENCES repo_archive_category(id) ON DELETE RESTRICT,
            CONSTRAINT repo_archive_tenant_id_fkey
                FOREIGN KEY (tenant_id) REFERENCES iam_tenant(id) ON DELETE CASCADE
        ) PARTITION BY RANGE ("ND")
    """)

    # 年度子分区
    for year in range(_PARTITION_START, _PARTITION_END):
        op.execute(f"""
            CREATE TABLE repo_archive_{year}
            PARTITION OF repo_archive
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    # 兜底分区（超出范围的年度）
    op.execute("""
        CREATE TABLE repo_archive_default
        PARTITION OF repo_archive DEFAULT
    """)

    # 分区表全局索引
    op.execute('CREATE INDEX ix_repo_archive_DH        ON repo_archive ("DH")')
    op.execute('CREATE INDEX ix_repo_archive_QZH       ON repo_archive ("QZH")')
    op.execute('CREATE INDEX ix_repo_archive_TM        ON repo_archive ("TM")')
    op.execute('CREATE INDEX ix_repo_archive_RZZ       ON repo_archive ("RZZ")')
    op.execute('CREATE INDEX ix_repo_archive_fonds_id  ON repo_archive (fonds_id)')
    op.execute('CREATE INDEX ix_repo_archive_catalog   ON repo_archive (catalog_id)')
    op.execute('CREATE INDEX ix_repo_archive_tenant_category ON repo_archive (tenant_id, category_id)')
    op.execute(
        "CREATE INDEX ix_repo_archive_ext_fields_gin "
        "ON repo_archive USING GIN (ext_fields jsonb_path_ops)"
    )

    # ── 4. 创建临时库 repo_archive_staging ───────────────────────────────────
    op.create_table(
        "repo_archive_staging",
        sa.Column("id", sa.UUID(), nullable=False,
                  server_default=sa.text("gen_random_uuid()"), comment="唯一标识"),
        sa.Column("fonds_id", sa.UUID(), nullable=False),
        sa.Column("catalog_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("DH", sa.String(100), nullable=True,
                  comment="档号（规则生成，可手动覆盖）"),
        sa.Column("QZH", sa.String(50), nullable=False, comment="全宗号"),
        sa.Column("TM", sa.String(512), nullable=False, comment="题名"),
        sa.Column("RZZ", sa.String(200), nullable=True, comment="责任者"),
        sa.Column("ND", sa.Integer(), nullable=True, comment="年度"),
        sa.Column("WJRQ", sa.String(20), nullable=True, comment="文件日期"),
        sa.Column("YS", sa.Integer(), nullable=True, comment="页数"),
        sa.Column("MJ", sa.String(20), nullable=False, server_default="public",
                  comment="密级"),
        sa.Column("BGQX", sa.String(20), nullable=False, server_default="permanent",
                  comment="保管期限"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft",
                  comment="工作流状态: draft | pending_review | rejected"),
        sa.Column("ext_fields", postgresql.JSONB(), nullable=True,
                  comment="门类私有字段"),
        sa.Column("embedding_status", sa.String(20), nullable=False,
                  server_default="pending"),
        sa.Column("es_synced_at", sa.String(30), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("update_time", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("create_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id", name="repo_archive_staging_pkey"),
        sa.ForeignKeyConstraint(
            ["fonds_id"], ["repo_fonds.id"], ondelete="CASCADE",
            name="repo_archive_staging_fonds_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["catalog_id"], ["repo_catalog.id"], ondelete="CASCADE",
            name="repo_archive_staging_catalog_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["repo_archive_category.id"], ondelete="RESTRICT",
            name="repo_archive_staging_category_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE",
            name="repo_archive_staging_tenant_id_fkey",
        ),
    )
    op.create_index("ix_repo_archive_staging_fonds_id",   "repo_archive_staging", ["fonds_id"])
    op.create_index("ix_repo_archive_staging_catalog_id", "repo_archive_staging", ["catalog_id"])
    op.create_index("ix_repo_archive_staging_category_id","repo_archive_staging", ["category_id"])
    op.create_index("ix_repo_archive_staging_DH",         "repo_archive_staging", ["DH"])
    op.create_index("ix_repo_archive_staging_QZH",        "repo_archive_staging", ["QZH"])
    op.create_index("ix_repo_archive_staging_TM",         "repo_archive_staging", ["TM"])
    op.create_index("ix_repo_archive_staging_RZZ",        "repo_archive_staging", ["RZZ"])
    op.create_index("ix_repo_archive_staging_tenant_id",  "repo_archive_staging", ["tenant_id"])
    op.execute(
        "CREATE INDEX ix_repo_archive_staging_ext_gin "
        "ON repo_archive_staging USING GIN (ext_fields jsonb_path_ops)"
    )

    # ── 5. 创建附件表 repo_archive_attachment ────────────────────────────────
    op.create_table(
        "repo_archive_attachment",
        sa.Column("id", sa.UUID(), nullable=False,
                  server_default=sa.text("gen_random_uuid()"), comment="唯一标识"),
        sa.Column("archive_id", sa.UUID(), nullable=False,
                  comment="档案记录 ID（临时库或正式库，无 FK 约束）"),
        sa.Column("is_staging", sa.Boolean(), nullable=False,
                  server_default=sa.text("true"),
                  comment="True=临时库附件，False=正式库附件"),
        sa.Column("is_primary", sa.Boolean(), nullable=False,
                  server_default=sa.text("true"), comment="是否主附件"),
        sa.Column("original_name", sa.String(512), nullable=False,
                  comment="原始文件名"),
        sa.Column("storage_key", sa.String(1024), nullable=False,
                  comment="对象存储路径"),
        sa.Column("storage_bucket", sa.String(255), nullable=False,
                  comment="存储桶名"),
        sa.Column("file_size", sa.BigInteger(), nullable=True,
                  comment="文件大小（字节）"),
        sa.Column("file_format", sa.String(50), nullable=True,
                  comment="文件格式（pdf/jpg/…）"),
        sa.Column("page_count", sa.Integer(), nullable=True,
                  comment="页数（PDF）"),
        sa.Column("sha256_hash", sa.String(64), nullable=True,
                  comment="SHA256 完整性校验值"),
        sa.Column("sort_order", sa.Integer(), nullable=False,
                  server_default=sa.text("0"), comment="附件排序"),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("update_time", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("create_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id", name="repo_archive_attachment_pkey"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE",
            name="repo_archive_attachment_tenant_id_fkey",
        ),
    )
    op.create_index(
        "ix_repo_archive_attachment_archive_id", "repo_archive_attachment", ["archive_id"]
    )
    op.create_index(
        "ix_repo_archive_attachment_tenant_id", "repo_archive_attachment", ["tenant_id"]
    )


def downgrade() -> None:
    # 删除新建的表（CASCADE 清理索引和 FK）
    op.drop_table("repo_archive_attachment")
    op.drop_table("repo_archive_staging")
    op.execute("DROP TABLE IF EXISTS repo_archive CASCADE")

    # 恢复 repo_catalog 字段
    op.drop_index("ix_repo_catalog_volume_archive_id", table_name="repo_catalog")
    op.drop_column("repo_catalog", "volume_archive_id")
    op.drop_column("repo_catalog", "catalog_type")
    op.add_column(
        "repo_catalog",
        sa.Column(
            "org_mode", sa.String(20), nullable=False,
            server_default="by_item",
            comment="整理方式: by_item | by_volume",
        ),
    )

    # 重建最简旧版 repo_archive（无数据）
    op.execute("""
        CREATE TABLE repo_archive (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            fonds_id    UUID        NOT NULL,
            catalog_id  UUID        NOT NULL,
            category_id UUID        NOT NULL,
            parent_id   UUID,
            level       VARCHAR(10) NOT NULL DEFAULT 'item',
            "DH"        VARCHAR(100),
            "QZH"       VARCHAR(50)  NOT NULL,
            "MLH"       VARCHAR(50),
            "AJH"       VARCHAR(50),
            "JH"        VARCHAR(50),
            "TM"        VARCHAR(512) NOT NULL,
            "RZZ"       VARCHAR(200),
            "ND"        INTEGER,
            "WJRQ"      VARCHAR(20),
            "YS"        INTEGER,
            "MJ"        VARCHAR(20)  NOT NULL DEFAULT 'public',
            "BGQX"      VARCHAR(20)  NOT NULL DEFAULT 'permanent',
            status      VARCHAR(20)  NOT NULL DEFAULT 'active',
            ext_fields  JSONB,
            storage_key     VARCHAR(1024),
            storage_bucket  VARCHAR(255),
            file_size       BIGINT,
            file_format     VARCHAR(50),
            sha256_hash     VARCHAR(64),
            embedding_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            es_synced_at     VARCHAR(30),
            tenant_id   UUID,
            create_time TIMESTAMPTZ NOT NULL DEFAULT now(),
            update_time TIMESTAMPTZ NOT NULL DEFAULT now(),
            create_by   UUID,
            is_deleted  BOOLEAN NOT NULL DEFAULT false,
            PRIMARY KEY (id)
        )
    """)
