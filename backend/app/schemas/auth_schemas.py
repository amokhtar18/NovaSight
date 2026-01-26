"""
NovaSight Authentication Schemas
================================

Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
import re


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    tenant_slug: Optional[str] = Field(None, description="Tenant slug for multi-tenant login")


class RegisterRequest(BaseModel):
    """User registration request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=12, description="User password (min 12 chars)")
    name: str = Field(..., min_length=1, max_length=100, description="User display name")
    tenant_slug: str = Field(..., min_length=3, max_length=50, description="Tenant slug")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean name."""
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        return v
    
    @field_validator('tenant_slug')
    @classmethod
    def validate_tenant_slug(cls, v: str) -> str:
        """Validate tenant slug format."""
        v = v.lower().strip()
        if not re.match(r'^[a-z][a-z0-9-]{2,49}$', v):
            raise ValueError('Tenant slug must start with letter, contain only lowercase letters, numbers, and hyphens')
        return v


class TokenResponse(BaseModel):
    """Token response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")


class UserInfo(BaseModel):
    """User information schema."""
    
    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User display name")
    tenant_id: str = Field(..., description="Tenant UUID")
    roles: List[str] = Field(default=[], description="User roles")


class LoginResponse(BaseModel):
    """Login response schema."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    user: UserInfo = Field(..., description="User information")
