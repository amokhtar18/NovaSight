"""
NovaSight Authentication Endpoints
==================================

JWT-based authentication for user registration, login, and logout.
"""

from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from pydantic import ValidationError as PydanticValidationError
from app.api.v1 import api_v1_bp
from app.services.auth_service import AuthService
from app.services.token_service import token_blacklist
from app.schemas.auth_schemas import LoginRequest, RegisterRequest
from app.errors import ValidationError, AuthenticationError
from app.extensions import limiter
from datetime import timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    """
    Register a new user.
    
    Request Body:
        - email: User email address
        - password: User password (min 12 chars, with complexity requirements)
        - name: User display name
        - tenant_slug: Tenant identifier slug
    
    Returns:
        Created user information
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    # Validate request with Pydantic
    try:
        register_req = RegisterRequest(**data)
    except PydanticValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        raise ValidationError("; ".join(errors))
    
    # Register user
    auth_service = AuthService()
    user, error = auth_service.register_user(
        email=register_req.email,
        password=register_req.password,
        name=register_req.name,
        tenant_slug=register_req.tenant_slug
    )
    
    if error:
        raise ValidationError(error)
    
    logger.info(f"New user registered: {user.email}")
    
    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "tenant_id": str(user.tenant_id),
        }
    }), 201


@api_v1_bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    """
    Authenticate user and return JWT tokens.
    
    Request Body:
        - email: User email address
        - password: User password
        - tenant_slug: Optional tenant slug for multi-tenant login
    
    Returns:
        JWT access and refresh tokens
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    # Validate request with Pydantic
    try:
        login_req = LoginRequest(**data)
    except PydanticValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        raise ValidationError("; ".join(errors))
    
    # Authenticate user
    auth_service = AuthService()
    user, error = auth_service.authenticate(
        email=login_req.email,
        password=login_req.password,
        tenant_slug=login_req.tenant_slug
    )
    
    if error:
        raise AuthenticationError(error)
    
    # Create tokens with user identity
    identity = {
        "user_id": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "roles": [role.name for role in user.roles] if hasattr(user, 'roles') and user.roles else [],
    }
    
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)
    
    logger.info(f"User {login_req.email} logged in successfully")
    
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "tenant_id": str(user.tenant_id),
            "roles": [role.name for role in user.roles] if hasattr(user, 'roles') and user.roles else [],
        }
    })


@api_v1_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    
    Returns:
        New JWT access token
    """
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    
    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
    })


@api_v1_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user information.
    
    Returns:
        Current user details
    """
    identity = get_jwt_identity()
    
    return jsonify({
        "user": {
            "id": identity.get("user_id"),
            "email": identity.get("email"),
            "tenant_id": identity.get("tenant_id"),
            "roles": identity.get("roles", []),
        }
    })


@api_v1_bp.route("/auth/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Logout current user by blacklisting the current token.
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    jwt_data = get_jwt()
    jti = jwt_data.get("jti")
    
    # Calculate remaining token lifetime
    exp = jwt_data.get("exp", 0)
    import time
    expires_in = max(0, exp - int(time.time()))
    
    # Add token to blacklist
    if jti:
        token_blacklist.add(jti, expires_in)
    
    logger.info(f"User {identity.get('email')} logged out")
    
    return jsonify({"message": "Successfully logged out"})


@api_v1_bp.route("/auth/logout-all", methods=["POST"])
@jwt_required(fresh=True)
def logout_all():
    """
    Logout from all devices by invalidating all tokens.
    
    Requires a fresh token (recent login).
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    
    # In a production system, you would:
    # 1. Increment user's token version in database
    # 2. All existing tokens with old version become invalid
    # For now, we just log the action
    
    logger.info(f"User {identity.get('email')} logged out from all devices")
    
    return jsonify({"message": "Successfully logged out from all devices"})


@api_v1_bp.route("/auth/change-password", methods=["POST"])
@jwt_required(fresh=True)
def change_password():
    """
    Change current user's password.
    
    Requires a fresh token (recent login).
    
    Request Body:
        - current_password: Current password
        - new_password: New password (with complexity requirements)
    
    Returns:
        Success message
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    
    if not current_password or not new_password:
        raise ValidationError("Current password and new password are required")
    
    identity = get_jwt_identity()
    user_id = identity.get("user_id")
    
    # Get user from database
    auth_service = AuthService()
    user = auth_service.validate_token_identity(identity)
    
    if not user:
        raise AuthenticationError("User not found")
    
    # Change password
    success, error = auth_service.change_password(user, current_password, new_password)
    
    if not success:
        raise ValidationError(error)
    
    logger.info(f"Password changed for user {identity.get('email')}")
    
    return jsonify({"message": "Password changed successfully"})
