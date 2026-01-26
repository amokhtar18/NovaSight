"""
NovaSight Authentication Endpoints
==================================

JWT-based authentication for user login/logout.
"""

from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from app.api.v1 import api_v1_bp
from app.services.auth_service import AuthService
from app.schemas.auth_schemas import LoginRequest, TokenResponse
from app.errors import ValidationError, AuthenticationError
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT tokens.
    
    Request Body:
        - email: User email address
        - password: User password
        - tenant_id: Optional tenant identifier
    
    Returns:
        JWT access and refresh tokens
    """
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    email = data.get("email")
    password = data.get("password")
    tenant_id = data.get("tenant_id")
    
    if not email or not password:
        raise ValidationError("Email and password required")
    
    # Authenticate user
    auth_service = AuthService()
    user = auth_service.authenticate(email, password, tenant_id)
    
    if not user:
        raise AuthenticationError("Invalid credentials")
    
    # Create tokens with user identity
    identity = {
        "user_id": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "roles": [role.name for role in user.roles],
    }
    
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)
    
    logger.info(f"User {email} logged in successfully")
    
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "tenant_id": str(user.tenant_id),
            "roles": [role.name for role in user.roles],
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
    Logout current user (invalidate token).
    
    Note: In a production system, this would add the token to a blocklist.
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    jti = get_jwt()["jti"]
    
    # TODO: Add token to Redis blocklist for true invalidation
    # redis_client.setex(f"token_blocklist:{jti}", ACCESS_EXPIRES, "true")
    
    logger.info(f"User {identity.get('email')} logged out")
    
    return jsonify({"message": "Successfully logged out"})
