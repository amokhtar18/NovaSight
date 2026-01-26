"""
NovaSight Error Handlers
========================

Global error handlers and custom exceptions.
"""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)


class NovaSightException(Exception):
    """Base exception for NovaSight application."""
    
    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"
    
    def __init__(self, message: str = None, status_code: int = None, error_code: str = None, details: dict = None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(NovaSightException):
    """Raised when input validation fails."""
    status_code = 400
    error_code = "VALIDATION_ERROR"
    message = "Invalid input data"


class AuthenticationError(NovaSightException):
    """Raised when authentication fails."""
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication required"


class AuthorizationError(NovaSightException):
    """Raised when authorization fails."""
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    message = "Access denied"


class NotFoundError(NovaSightException):
    """Raised when a resource is not found."""
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(NovaSightException):
    """Raised when a resource conflict occurs."""
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict"


class TenantNotFoundError(NotFoundError):
    """Raised when tenant is not found."""
    error_code = "TENANT_NOT_FOUND"
    message = "Tenant not found"


class ConnectionTestError(NovaSightException):
    """Raised when database connection test fails."""
    status_code = 400
    error_code = "CONNECTION_TEST_FAILED"
    message = "Database connection test failed"


class TemplateRenderError(NovaSightException):
    """Raised when template rendering fails."""
    status_code = 500
    error_code = "TEMPLATE_RENDER_ERROR"
    message = "Failed to render template"


class AirflowAPIError(NovaSightException):
    """Raised when Airflow API call fails."""
    status_code = 502
    error_code = "AIRFLOW_API_ERROR"
    message = "Airflow API error"


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers with Flask application."""
    
    @app.errorhandler(NovaSightException)
    def handle_novasight_exception(error: NovaSightException):
        """Handle NovaSight custom exceptions."""
        logger.warning(f"{error.error_code}: {error.message}", exc_info=True)
        return jsonify(error.to_dict()), error.status_code
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handle Werkzeug HTTP exceptions."""
        logger.warning(f"HTTP {error.code}: {error.description}")
        return jsonify({
            "error": {
                "code": f"HTTP_{error.code}",
                "message": error.description,
                "details": {},
            }
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {error}", exc_info=True)
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            }
        }), 500
