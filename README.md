# CaseLedger AI

Independent full-stack portfolio project for reliable, AI-ready processing of regulated case files.

It demonstrates the engineering problems common to document-heavy professional workflows: tenant-safe data models, repeatable imports, structured extraction, retrieval across case documents, grounded outputs with citations, auditability, testing and containerized deployment.

## Why this is not a generic CRUD app

The core behavior is built around **document ingestion and repeat processing**, not forms over database tables. Re-uploading the same content is idempotent, all data is tenant-scoped, retrieval returns evidence, structured extraction is reviewable, and generated answers are explicitly marked for human review.

## Stack

Python 3.12, FastAPI, SQLAlchemy, PostgreSQL/SQLite, HTML/CSS/JavaScript, Pytest, Docker Compose, GitHub Actions.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000` and use the preconfigured demo API key `demo-key` in the web interface.

## Run with PostgreSQL

```bash
docker compose up --build
```

Then open `http://localhost:8000`.

## Test

```bash
pytest -q
ruff check app tests
python -m compileall -q app
```

## API examples

Create a case:

```bash
curl -X POST http://localhost:8000/api/cases \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: demo-key' \
  -d '{"external_ref":"CASE-2026-001","title":"Supplier dispute"}'
```

Ingest a document:

```bash
curl -X POST http://localhost:8000/api/cases/1/documents \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: demo-key' \
  -d '{"filename":"notice.txt","text":"Case IN 142/26. Amount 23.450,80 €. Hearing 14.05.2026."}'
```

Ask a grounded question:

```bash
curl -X POST http://localhost:8000/api/cases/1/answer \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: demo-key' \
  -d '{"question":"What is the claim amount and hearing date?"}'
```

## Security and privacy design

- Tenant-scoped queries and constraints.
- Cross-tenant resource lookup returns 404.
- No external LLM call by default, so demo case content stays local.
- Citation-first answers and mandatory human-review flag.
- Audit trail for sensitive operations.
- No secrets committed; `.env.example` contains only documentation values.

## Repository structure

```text
app/                 FastAPI app, data model, services and browser UI
tests/               API, idempotency, tenant-isolation and audit tests
docs/ARCHITECTURE.md Architecture and production-extension notes
.github/workflows/   CI pipeline
Dockerfile           Application image
docker-compose.yml   App + PostgreSQL local production-style stack
```
