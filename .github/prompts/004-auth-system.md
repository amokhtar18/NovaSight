# 004 - Authentication System

## Metadata

```yaml
prompt_id: "004"
phase: 1
agent: "@backend"
model: "opus 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["003"]
```

## Objective

Implement JWT-based authentication with secure password handling, token refresh, and session management.

## Task Description

Create a complete authentication system with:

1. **User Registration** - With email validation
2. **Login** - Returns access + refresh tokens
3. **Token Refresh** - Extend session without re-login
4. **Logout** - Token blacklisting
5. **Password Management** - Secure hashing with Argon2

## Requirements

### Auth Endpoints

```python
# POST /api/v1/auth/register
{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "name": "John Doe",
    "tenant_slug": "acme-corp"
}

# POST /api/v1/auth/login
{
    "email": "user@example.com",
    "password": "SecurePass123!"
}

# Response
{
    "success": true,
    "data": {
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "token_type": "Bearer",
        "expires_in": 3600,
        "user": {
            "id": "uuid",
            "email": "user@example.com",
            "name": "John Doe",
            "tenant": { ... }
        }
    }
}

# POST /api/v1/auth/refresh
# Authorization: Bearer <refresh_token>

# POST /api/v1/auth/logout
# Authorization: Bearer <access_token>
```

### Password Service

```python
# backend/app/services/password_service.py
import argon2

class PasswordService:
    def __init__(self):
        self.hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4
        )
    
    def hash(self, password: str) -> str:
        return self.hasher.hash(password)
    
    def verify(self, password: str, hash: str) -> bool:
        try:
            return self.hasher.verify(hash, password)
        except argon2.exceptions.VerifyMismatchError:
            return False
    
    def validate_strength(self, password: str) -> tuple[bool, str]:
        # Min 12 chars, uppercase, lowercase, digit, special
        ...
```

### JWT Configuration

```python
# JWT claims structure
{
    "sub": "user_id",
    "tenant_id": "tenant_uuid",
    "roles": ["admin", "analyst"],
    "permissions": ["datasources.view", "analytics.query"],
    "iat": 1234567890,
    "exp": 1234571490
}
```

### Token Blacklist

```python
# Redis-based token blacklist for logout
class TokenBlacklist:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def add(self, jti: str, expires_in: int):
        self.redis.setex(f"blacklist:{jti}", expires_in, "1")
    
    def is_blacklisted(self, jti: str) -> bool:
        return self.redis.exists(f"blacklist:{jti}")
```

## Expected Output

```
backend/app/
├── api/v1/
│   └── auth.py              # Auth endpoints
├── services/
│   ├── auth_service.py      # Auth business logic
│   └── password_service.py  # Password handling
├── schemas/
│   └── auth_schemas.py      # Pydantic schemas
└── middleware/
    └── jwt_handlers.py      # JWT callbacks
```

## Acceptance Criteria

- [ ] Registration creates user with hashed password
- [ ] Login returns valid JWT tokens
- [ ] Token refresh works correctly
- [ ] Logout invalidates token
- [ ] Password strength validation works
- [ ] Rate limiting on login (5/minute)
- [ ] Failed login tracking (lockout after 5 failures)

## Reference Documents

- [Security Agent](../agents/security-agent.agent.md)
- [BRD - Epic 7](../../docs/requirements/BRD_Part4.md)
