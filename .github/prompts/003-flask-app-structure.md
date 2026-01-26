# 003 - Flask App Structure

## Metadata

```yaml
prompt_id: "003"
phase: 1
agent: "@backend"
model: "opus 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["001", "002"]
```

## Objective

Create the Flask application structure using the app factory pattern with proper organization for a multi-tenant SaaS application.

## Task Description

Implement the Flask backend with:

1. **App Factory Pattern** - `create_app()` function
2. **Extension Management** - SQLAlchemy, JWT, CORS, etc.
3. **Blueprint Organization** - Versioned API structure
4. **Configuration Management** - Environment-based configs
5. **Error Handling** - Global error handlers

## Requirements

### Application Structure

```python
# backend/app/__init__.py
from flask import Flask
from app.extensions import db, jwt, cors, migrate
from app.config import config

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.api.v1 import api_v1
    app.register_blueprint(api_v1, url_prefix='/api/v1')
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register middleware
    register_middleware(app)
    
    return app
```

### Configuration Classes

```python
# backend/app/config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
class ProductionConfig(Config):
    DEBUG = False
```

### Extensions Setup

```python
# backend/app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
migrate = Migrate()
```

## Expected Output

```
backend/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py             # Configuration classes
│   ├── extensions.py         # Flask extensions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tenant.py
│   │   ├── user.py
│   │   └── mixins.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py
│   ├── services/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── error_handlers.py
│   └── utils/
│       └── __init__.py
├── migrations/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── unit/
├── requirements.txt
├── requirements-dev.txt
└── run.py
```

## Acceptance Criteria

- [ ] `flask run` starts the application
- [ ] `/api/v1/health` returns 200 OK
- [ ] SQLAlchemy connects to PostgreSQL
- [ ] JWT extension configured
- [ ] CORS allows frontend origin
- [ ] Error handlers return JSON responses
- [ ] Tests pass with pytest

## Reference Documents

- [Backend Agent](../agents/backend-agent.agent.md)
- [Flask API Skill](../skills/flask-api/SKILL.md)
