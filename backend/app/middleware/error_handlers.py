"""
NovaSight Error Handlers
========================

Global error handlers for consistent JSON error responses.
"""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        return jsonify({
            "error": "bad_request",
            "message": str(error.description) if hasattr(error, 'description') else "Bad request",
            "status_code": 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors."""
        return jsonify({
            "error": "unauthorized",
            "message": "Authentication required",
            "status_code": 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors."""
        return jsonify({
            "error": "forbidden",
            "message": "You don't have permission to access this resource",
            "status_code": 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors."""
        return jsonify({
            "error": "not_found",
            "message": "Resource not found",
            "status_code": 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        return jsonify({
            "error": "method_not_allowed",
            "message": "Method not allowed for this endpoint",
            "status_code": 405
        }), 405
    
    @app.errorhandler(409)
    def conflict(error):
        """Handle 409 Conflict errors."""
        return jsonify({
            "error": "conflict",
            "message": str(error.description) if hasattr(error, 'description') else "Resource conflict",
            "status_code": 409
        }), 409
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors."""
        return jsonify({
            "error": "unprocessable_entity",
            "message": str(error.description) if hasattr(error, 'description') else "Validation error",
            "status_code": 422
        }), 422
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Too Many Requests errors."""
        return jsonify({
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "status_code": 429
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all other HTTP exceptions."""
        return jsonify({
            "error": error.name.lower().replace(" ", "_"),
            "message": error.description,
            "status_code": error.code
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions."""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500
