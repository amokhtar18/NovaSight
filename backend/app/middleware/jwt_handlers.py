"""
NovaSight JWT Handlers
======================

Flask-JWT-Extended callback handlers for token validation.
"""

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from app.services.token_service import token_blacklist
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)


def register_jwt_handlers(jwt: JWTManager) -> None:
    """
    Register JWT callback handlers.
    
    Args:
        jwt: Flask-JWT-Extended JWTManager instance
    """
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload) -> bool:
        """
        Check if a token has been revoked (blacklisted).
        
        This callback is called for every protected endpoint to verify
        the token hasn't been logged out.
        """
        jti = jwt_payload.get("jti")
        return token_blacklist.is_blacklisted(jti)
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """Handle revoked token access."""
        return jsonify({
            "error": "token_revoked",
            "message": "Token has been revoked. Please log in again.",
            "status_code": 401
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """Handle expired token access."""
        return jsonify({
            "error": "token_expired",
            "message": "Token has expired. Please refresh or log in again.",
            "status_code": 401
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """Handle invalid token."""
        return jsonify({
            "error": "invalid_token",
            "message": "Token is invalid or malformed.",
            "status_code": 401
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """Handle missing token."""
        return jsonify({
            "error": "authorization_required",
            "message": "Authorization token is required.",
            "status_code": 401
        }), 401
    
    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        """Handle non-fresh token for sensitive operations."""
        return jsonify({
            "error": "fresh_token_required",
            "message": "Fresh token required for this operation. Please log in again.",
            "status_code": 401
        }), 401
    
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        """
        Callback to convert user object to identity for token.
        
        Args:
            user: User dict or object passed to create_access_token
        
        Returns:
            Identity to embed in token
        """
        if isinstance(user, dict):
            return user
        # If it's a User model object
        return {
            "user_id": str(user.id),
            "email": user.email,
            "tenant_id": str(user.tenant_id),
            "roles": [role.name for role in user.roles] if hasattr(user, 'roles') else [],
        }
    
    @jwt.user_lookup_loader
    def user_lookup_callback(jwt_header, jwt_payload):
        """
        Callback to load user from token identity.
        
        Returns:
            User object or None
        """
        identity = jwt_payload.get("sub")
        if not identity or not isinstance(identity, dict):
            return None
        
        auth_service = AuthService()
        return auth_service.validate_token_identity(identity)
    
    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):
        """
        Add additional claims to access token.
        
        Args:
            identity: User identity dict
        
        Returns:
            Additional claims to add
        """
        if not isinstance(identity, dict):
            return {}
        
        return {
            "tenant_id": identity.get("tenant_id"),
            "roles": identity.get("roles", []),
            "permissions": identity.get("permissions", []),
        }


def init_jwt_handlers(app: Flask) -> None:
    """
    Initialize JWT handlers for Flask app.
    
    Args:
        app: Flask application instance
    """
    from app.extensions import jwt
    register_jwt_handlers(jwt)
