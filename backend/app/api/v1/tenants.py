"""
NovaSight Tenant Management Endpoints
=====================================

Multi-tenant administration endpoints.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1_bp
from app.services.tenant_service import TenantService
from app.decorators import require_roles
from app.errors import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/tenants", methods=["GET"])
@jwt_required()
@require_roles(["super_admin"])
def list_tenants():
    """
    List all tenants (Super Admin only).
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - status: Filter by status (active, suspended)
    
    Returns:
        Paginated list of tenants
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    
    tenant_service = TenantService()
    result = tenant_service.list_tenants(page=page, per_page=per_page, status=status)
    
    return jsonify(result)


@api_v1_bp.route("/tenants", methods=["POST"])
@jwt_required()
@require_roles(["super_admin"])
def create_tenant():
    """
    Create a new tenant (Super Admin only).
    
    Request Body:
        - name: Tenant display name
        - slug: Unique tenant identifier
        - plan: Subscription plan (basic, professional, enterprise)
        - settings: Optional tenant settings
    
    Returns:
        Created tenant details
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    required_fields = ["name", "slug"]
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"Field '{field}' is required")
    
    tenant_service = TenantService()
    tenant = tenant_service.create_tenant(
        name=data["name"],
        slug=data["slug"],
        plan=data.get("plan", "basic"),
        settings=data.get("settings", {}),
    )
    
    logger.info(f"Tenant '{data['name']}' created with slug '{data['slug']}'")
    
    return jsonify({"tenant": tenant.to_dict()}), 201


@api_v1_bp.route("/tenants/<tenant_id>", methods=["GET"])
@jwt_required()
@require_roles(["super_admin", "tenant_admin"])
def get_tenant(tenant_id: str):
    """
    Get tenant details.
    
    Args:
        tenant_id: Tenant UUID
    
    Returns:
        Tenant details
    """
    identity = get_jwt_identity()
    
    # Tenant admins can only view their own tenant
    if "super_admin" not in identity.get("roles", []):
        if identity.get("tenant_id") != tenant_id:
            raise NotFoundError("Tenant not found")
    
    tenant_service = TenantService()
    tenant = tenant_service.get_tenant(tenant_id)
    
    if not tenant:
        raise NotFoundError("Tenant not found")
    
    return jsonify({"tenant": tenant.to_dict()})


@api_v1_bp.route("/tenants/<tenant_id>", methods=["PATCH"])
@jwt_required()
@require_roles(["super_admin", "tenant_admin"])
def update_tenant(tenant_id: str):
    """
    Update tenant settings.
    
    Args:
        tenant_id: Tenant UUID
    
    Request Body:
        - name: Tenant display name
        - settings: Tenant settings object
        - status: Tenant status (super_admin only)
    
    Returns:
        Updated tenant details
    """
    identity = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    # Tenant admins can only update their own tenant
    if "super_admin" not in identity.get("roles", []):
        if identity.get("tenant_id") != tenant_id:
            raise NotFoundError("Tenant not found")
        # Tenant admins cannot change status
        data.pop("status", None)
    
    tenant_service = TenantService()
    tenant = tenant_service.update_tenant(tenant_id, **data)
    
    if not tenant:
        raise NotFoundError("Tenant not found")
    
    logger.info(f"Tenant {tenant_id} updated")
    
    return jsonify({"tenant": tenant.to_dict()})
