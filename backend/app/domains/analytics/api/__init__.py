"""NovaSight Analytics Domain - API Routes."""

# Import routes to register with blueprint
from app.domains.analytics.api import dashboard_routes  # noqa: F401
from app.domains.analytics.api import chart_routes  # noqa: F401
