# Kidemia

Kidemia is a modern api project built with [FastAPI](https://fastapi.tiangolo.com/) for speed, reliability, and scalability.  
It follows the DDD pattern and respect repositories approach structure. The API serves as the foundation for APIs powering Kidemia clients.

---

## 🚀 Features
- FastAPI-based REST API
- Async support for high performance
- PostgreSQL 
- Automatic interactive API docs (Swagger & ReDoc)
- Docker-ready for easy deployment
- Structured project layout for scalability

---

## 📦 Requirements
- Python 3.11+
- [Poetry](https://python-poetry.org/) or `uv` (preferred) for dependency management
- PostgreSQL (local or Google Cloud SQL)
- Docker (optional, for containerized deployment)

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/ogbonnaohakwe/kidemia-backend#
cd kidemia
```
## Create virtual environment & install dependencies

### Using uv
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```
## Configure environment

### Create a .env file in the project root:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/kidemia
SECRET_KEY=your-secret-key
DEBUG=True
```

## Run the development server

```bash
uvicorn app.main:app --reload
```

Visit the interactive docs:

Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc
