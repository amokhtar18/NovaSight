"""
NovaSight Pagination Utilities
==============================

Helpers for API pagination.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, TypeVar, Generic
from flask import request, current_app
from sqlalchemy.orm import Query

T = TypeVar('T')


@dataclass
class PaginationParams:
    """Pagination parameters extracted from request."""
    page: int
    per_page: int
    
    @classmethod
    def from_request(cls) -> "PaginationParams":
        """Extract pagination params from current request."""
        default_per_page = current_app.config.get("DEFAULT_PAGE_SIZE", 20)
        max_per_page = current_app.config.get("MAX_PAGE_SIZE", 100)
        
        try:
            page = max(1, int(request.args.get("page", 1)))
        except (ValueError, TypeError):
            page = 1
        
        try:
            per_page = min(max_per_page, max(1, int(request.args.get("per_page", default_per_page))))
        except (ValueError, TypeError):
            per_page = default_per_page
        
        return cls(page=page, per_page=per_page)
    
    @property
    def offset(self) -> int:
        """Calculate offset for SQL query."""
        return (self.page - 1) * self.per_page


@dataclass
class PaginatedResult(Generic[T]):
    """Container for paginated results."""
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool
    
    def to_dict(self, item_serializer=None) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        items = self.items
        if item_serializer:
            items = [item_serializer(item) for item in items]
        elif hasattr(self.items[0] if self.items else None, 'to_dict'):
            items = [item.to_dict() for item in self.items]
        
        return {
            "items": items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "per_page": self.per_page,
                "pages": self.pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
            }
        }


def paginate(query: Query, params: PaginationParams = None) -> PaginatedResult:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query to paginate.
        params: Pagination parameters (defaults to request params).
    
    Returns:
        PaginatedResult with items and metadata.
    """
    if params is None:
        params = PaginationParams.from_request()
    
    # Get total count
    total = query.count()
    
    # Calculate total pages
    pages = (total + params.per_page - 1) // params.per_page if total > 0 else 1
    
    # Get items for current page
    items = query.offset(params.offset).limit(params.per_page).all()
    
    return PaginatedResult(
        items=items,
        total=total,
        page=params.page,
        per_page=params.per_page,
        pages=pages,
        has_next=params.page < pages,
        has_prev=params.page > 1,
    )
