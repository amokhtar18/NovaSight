"""add versioning + soft delete to visual_models and create visual_model_versions

Revision ID: d1e3f5a7b2c8
Revises: b9d2e3f4a5c6
Create Date: 2026-03-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd1e3f5a7b2c8'
down_revision = 'c1f8a2b3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    # ── visual_models: add version + soft delete columns ────────────────
    op.add_column(
        'visual_models',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'visual_models',
        sa.Column(
            'is_deleted',
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        'visual_models',
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index(
        'ix_visual_models_is_deleted',
        'visual_models',
        ['is_deleted'],
    )

    # ── visual_model_versions: snapshot history table ───────────────────
    op.create_table(
        'visual_model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('model_path', sa.Text(), nullable=False),
        sa.Column('model_layer', sa.String(20), nullable=False),
        sa.Column('visual_config', postgresql.JSONB(), nullable=False),
        sa.Column('generated_sql', sa.Text(), nullable=True),
        sa.Column('generated_yaml', sa.Text(), nullable=True),
        sa.Column('materialization', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True, server_default=''),
        sa.Column(
            'change_type',
            sa.String(20),
            nullable=False,
            server_default='update',
        ),
        sa.Column('change_summary', sa.Text(), nullable=True, server_default=''),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenants.id'], ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['model_id'], ['visual_models.id'], ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'model_id', 'version', name='uq_visual_model_version',
        ),
    )
    op.create_index(
        'ix_visual_model_versions_tenant_id',
        'visual_model_versions',
        ['tenant_id'],
    )
    op.create_index(
        'ix_visual_model_versions_model_id',
        'visual_model_versions',
        ['model_id'],
    )


def downgrade():
    op.drop_index(
        'ix_visual_model_versions_model_id',
        table_name='visual_model_versions',
    )
    op.drop_index(
        'ix_visual_model_versions_tenant_id',
        table_name='visual_model_versions',
    )
    op.drop_table('visual_model_versions')

    op.drop_index('ix_visual_models_is_deleted', table_name='visual_models')
    op.drop_column('visual_models', 'deleted_at')
    op.drop_column('visual_models', 'is_deleted')
    op.drop_column('visual_models', 'version')
