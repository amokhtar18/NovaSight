"""
NovaSight API v1 Blueprint
==========================

Version 1 of the NovaSight REST API.
"""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

# Import and register route modules
from app.api.v1 import auth
from app.api.v1 import tenants
from app.api.v1 import users
from app.api.v1 import connections
from app.api.v1 import dags
