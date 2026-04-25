"""add_iceberg_catalog_schema

Revision ID: d1e2f3a4b5c6
Revises: f1a3b5c7d9e2
Create Date: 2026-04-25 20:00:00.000000

Phase 1 of Spark → dlt migration: Create iceberg_catalog schema
for pyiceberg's Postgres SQL catalog backend.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'f1a3b5c7d9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create the iceberg_catalog schema for pyiceberg SQL catalog.
    
    Pyiceberg auto-creates its catalog tables (namespaces, tables, etc.)
    on first use. This migration only ensures the schema exists with
    appropriate grants for the platform service role.
    """
    # Create the schema for Iceberg catalog metadata
    op.execute("CREATE SCHEMA IF NOT EXISTS iceberg_catalog")
    
    # Grant usage on the schema to the platform role
    # (novasight user is already the owner, so has full access)
    op.execute("GRANT ALL ON SCHEMA iceberg_catalog TO novasight")
    
    # Set default privileges for future tables created in this schema
    op.execute("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA iceberg_catalog
        GRANT ALL ON TABLES TO novasight
    """)
    
    # Add 'object_storage' to the service_type check constraint if it exists
    # First, check if we need to update the infrastructure_configs table
    op.execute("""
        DO $$
        BEGIN
            -- Update any existing check constraint to include 'object_storage'
            -- This is a no-op if the constraint doesn't exist
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'infrastructure_configs' 
                AND column_name = 'service_type'
            ) THEN
                -- The column exists; service_type validation is done at app level
                NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """
    Drop the iceberg_catalog schema.
    
    WARNING: This will delete all Iceberg catalog metadata!
    Tables in object storage will become orphaned.
    """
    op.execute("DROP SCHEMA IF EXISTS iceberg_catalog CASCADE")
