# NovaSight - Self-Service End-to-End BI Solution

<p align="center">
  <img src="docs/assets/logo.png" alt="NovaSight Logo" width="200"/>
</p>

<p align="center">
  <strong>Democratizing Data Analytics Through Low-Code/No-Code</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#documentation">Documentation</a>
</p>

---

## 🚀 Overview

NovaSight is a multi-tenant SaaS platform that enables users to ingest, transform, model, and visualize data without requiring programming expertise. Built with enterprise-grade security and governance at its core.

### Key Differentiators

- **🔒 Template-Based Architecture**: All code generation uses pre-approved, security-audited templates—no arbitrary code execution
- **🎯 Complete Self-Service**: From data ingestion to dashboard creation, users control the entire data lifecycle
- **🤖 AI-Powered Insights**: Local LLM integration (Ollama) for natural language data exploration
- **🏢 Enterprise Multi-Tenancy**: Complete tenant isolation with RBAC and Row-Level Security

## ✨ Features

### Data Ingestion
- Connect to PostgreSQL, Oracle, SQL Server, MySQL
- Visual schema browser and column mapping
- SCD Type 1 & 2 support
- Incremental load strategies

### Orchestration
- Visual DAG builder with drag-and-drop
- Apache Airflow integration
- Real-time monitoring and logs
- Alerting and notifications

### Transformation
- dbt integration for semantic modeling
- Visual join builder
- Calculated columns and metrics
- Data quality testing

### Analytics
- SQL editor with autocomplete
- Chart builder with 20+ visualization types
- Interactive dashboards
- AI-powered natural language queries

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (SPA)                     │
├─────────────────────────────────────────────────────────────┤
│                     Flask REST API                           │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  PostgreSQL  │  ClickHouse  │   Airflow    │    Ollama      │
│  (Metadata)  │ (Warehouse)  │(Orchestrator)│    (LLM)       │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Vite, TanStack Query, Shadcn/UI |
| Backend | Flask, SQLAlchemy, Pydantic, JWT |
| Compute | PySpark, dbt |
| Orchestration | Apache Airflow |
| Data Warehouse | ClickHouse |
| AI/LLM | Ollama (Local) |
| Metadata | PostgreSQL |
| Cache | Redis |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for frontend development)
- Python 3.11+ (for backend development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/novasight.git
   cd novasight
   ```

2. **Start infrastructure services**
   ```bash
   docker-compose up -d postgres redis clickhouse airflow-webserver airflow-scheduler
   ```

3. **Set up the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   flask db upgrade
   flask run
   ```

4. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5000
   - Airflow: http://localhost:8080 (airflow/airflow)

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| NovaSight | admin@novasight.dev | admin123 |
| Airflow | airflow | airflow |

## 📖 Documentation

- [Business Requirements (BRD)](docs/requirements/BRD.md)
- [Architecture Decisions](docs/requirements/Architecture_Decisions.md)
- [Implementation Plan](docs/implementation/IMPLEMENTATION_PLAN.md)
- [API Reference](docs/api/README.md)

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest --cov=app tests/

# Frontend tests
cd frontend
npm run test
```

## 🤝 Contributing

Please read our [Contributing Guide](CONTRIBUTING.md) before submitting a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by the NovaSight Team
</p>
