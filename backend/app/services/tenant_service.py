"""
NovaSight Tenant Service
========================

Multi-tenant management operations.
"""

from typing import Optional, Dict, Any, List
from app.extensions import db
from app.models.tenant import Tenant, TenantStatus, SubscriptionPlan
import logging
import uuid

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant management operations."""
    
    def list_tenants(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all tenants with pagination.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status
        
        Returns:
            Paginated list of tenants
        """
        query = Tenant.query
        
        if status:
            try:
                status_enum = TenantStatus(status)
                query = query.filter(Tenant.status == status_enum)
            except ValueError:
                pass
        
        query = query.order_by(Tenant.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            "tenants": [t.to_dict() for t in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            }
        }
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """
        Get tenant by ID.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            Tenant object or None
        """
        try:
            return Tenant.query.filter(Tenant.id == tenant_id).first()
        except Exception as e:
            logger.error(f"Error fetching tenant {tenant_id}: {e}")
            return None
    
    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Get tenant by slug.
        
        Args:
            slug: Tenant slug
        
        Returns:
            Tenant object or None
        """
        return Tenant.query.filter(Tenant.slug == slug).first()
    
    def create_tenant(
        self,
        name: str,
        slug: str,
        plan: str = "basic",
        settings: Optional[Dict[str, Any]] = None
    ) -> Tenant:
        """
        Create a new tenant.
        
        Args:
            name: Tenant display name
            slug: Unique tenant identifier
            plan: Subscription plan
            settings: Tenant settings
        
        Returns:
            Created Tenant object
        """
        # Validate slug uniqueness
        existing = self.get_tenant_by_slug(slug)
        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists")
        
        # Parse plan
        try:
            plan_enum = SubscriptionPlan(plan)
        except ValueError:
            plan_enum = SubscriptionPlan.BASIC
        
        tenant = Tenant(
            name=name,
            slug=slug.lower().replace(" ", "_"),
            plan=plan_enum,
            status=TenantStatus.ACTIVE,
            settings=settings or {},
        )
        
        db.session.add(tenant)
        db.session.commit()
        
        logger.info(f"Created tenant: {tenant.slug}")
        
        # TODO: Create tenant schema in database
        # self._create_tenant_schema(tenant)
        
        return tenant
    
    def update_tenant(
        self,
        tenant_id: str,
        **kwargs
    ) -> Optional[Tenant]:
        """
        Update tenant details.
        
        Args:
            tenant_id: Tenant UUID
            **kwargs: Fields to update
        
        Returns:
            Updated Tenant object or None
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        # Update allowed fields
        allowed_fields = ["name", "settings", "status", "plan"]
        
        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue
            
            if field == "status":
                try:
                    value = TenantStatus(value)
                except ValueError:
                    continue
            elif field == "plan":
                try:
                    value = SubscriptionPlan(value)
                except ValueError:
                    continue
            
            setattr(tenant, field, value)
        
        db.session.commit()
        logger.info(f"Updated tenant: {tenant.slug}")
        
        return tenant
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """
        Delete (archive) a tenant.
        
        Args:
            tenant_id: Tenant UUID
        
        Returns:
            True if successful
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.ARCHIVED
        db.session.commit()
        
        logger.info(f"Archived tenant: {tenant.slug}")
        
        return True
