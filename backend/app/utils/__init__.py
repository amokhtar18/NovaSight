"""
NovaSight Utilities Package
===========================

Common utility functions and helpers.
"""

from app.utils.encryption import encrypt_credential, decrypt_credential
from app.utils.pagination import paginate, PaginationParams
from app.utils.validators import validate_slug, validate_email
from app.utils.tenant_utils import (
    get_tenant_schema_name,
    create_tenant_schema,
    drop_tenant_schema,
    schema_exists,
    list_tenant_schemas,
    set_search_path,
    reset_search_path,
    execute_in_tenant_context,
    get_current_tenant_schema,
    validate_tenant_access,
    TenantSchemaContext,
)

__all__ = [
    # Encryption
    "encrypt_credential",
    "decrypt_credential",
    # Pagination
    "paginate",
    "PaginationParams",
    # Validators
    "validate_slug",
    "validate_email",
    # Tenant utilities
    "get_tenant_schema_name",
    "create_tenant_schema",
    "drop_tenant_schema",
    "schema_exists",
    "list_tenant_schemas",
    "set_search_path",
    "reset_search_path",
    "execute_in_tenant_context",
    "get_current_tenant_schema",
    "validate_tenant_access",
    "TenantSchemaContext",
]
