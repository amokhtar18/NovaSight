"""
NovaSight Validation Utilities
==============================

Common validation functions.
"""

import re
from typing import Optional


def validate_slug(slug: str, max_length: int = 100) -> Optional[str]:
    """
    Validate a URL-safe slug.
    
    Args:
        slug: The slug to validate.
        max_length: Maximum allowed length.
    
    Returns:
        Error message if invalid, None if valid.
    """
    if not slug:
        return "Slug is required"
    
    if len(slug) > max_length:
        return f"Slug must be {max_length} characters or less"
    
    if not re.match(r'^[a-z][a-z0-9-]*$', slug):
        return "Slug must start with a letter and contain only lowercase letters, numbers, and hyphens"
    
    if '--' in slug:
        return "Slug cannot contain consecutive hyphens"
    
    if slug.endswith('-'):
        return "Slug cannot end with a hyphen"
    
    return None


def validate_email(email: str) -> Optional[str]:
    """
    Validate an email address.
    
    Args:
        email: The email to validate.
    
    Returns:
        Error message if invalid, None if valid.
    """
    if not email:
        return "Email is required"
    
    if len(email) > 255:
        return "Email must be 255 characters or less"
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return "Invalid email format"
    
    return None


def validate_password(password: str) -> Optional[str]:
    """
    Validate a password meets security requirements.
    
    Args:
        password: The password to validate.
    
    Returns:
        Error message if invalid, None if valid.
    """
    if not password:
        return "Password is required"
    
    if len(password) < 8:
        return "Password must be at least 8 characters"
    
    if len(password) > 128:
        return "Password must be 128 characters or less"
    
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return "Password must contain at least one number"
    
    return None


def validate_cron(cron_expression: str) -> Optional[str]:
    """
    Validate a cron expression.
    
    Args:
        cron_expression: The cron expression to validate.
    
    Returns:
        Error message if invalid, None if valid.
    """
    if not cron_expression:
        return "Cron expression is required"
    
    parts = cron_expression.split()
    if len(parts) != 5:
        return "Cron expression must have exactly 5 parts (minute hour day month weekday)"
    
    # Basic validation for each field
    ranges = [
        (0, 59),   # minute
        (0, 23),   # hour
        (1, 31),   # day
        (1, 12),   # month
        (0, 6),    # weekday
    ]
    
    for i, (part, (min_val, max_val)) in enumerate(zip(parts, ranges)):
        if part == '*':
            continue
        
        # Handle step values like */5
        if part.startswith('*/'):
            try:
                step = int(part[2:])
                if step < 1:
                    return f"Invalid step value in field {i + 1}"
            except ValueError:
                return f"Invalid step value in field {i + 1}"
            continue
        
        # Handle ranges like 1-5
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start < min_val or end > max_val or start > end:
                    return f"Invalid range in field {i + 1}"
            except ValueError:
                return f"Invalid range in field {i + 1}"
            continue
        
        # Handle lists like 1,3,5
        if ',' in part:
            try:
                values = list(map(int, part.split(',')))
                if any(v < min_val or v > max_val for v in values):
                    return f"Value out of range in field {i + 1}"
            except ValueError:
                return f"Invalid list in field {i + 1}"
            continue
        
        # Single value
        try:
            value = int(part)
            if value < min_val or value > max_val:
                return f"Value out of range in field {i + 1}"
        except ValueError:
            return f"Invalid value in field {i + 1}"
    
    return None
