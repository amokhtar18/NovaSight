"""
NovaSight Authentication Schemas
================================

Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List


class LoginRequest(BaseModel):
    """Login request schema."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    tenant_id: Optional[str] = Field(None, description="Optional tenant identifier")


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
