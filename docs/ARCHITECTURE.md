# Architecture

CaseLedger AI is an independent portfolio project for regulated document workflows. It intentionally does not reproduce any employer's proprietary workflow.

## Components

- **FastAPI application layer**: tenant-scoped case, ingestion, retrieval, grounded-answer and audit APIs.
- **SQLAlchemy persistence**: SQLite for zero-setup local development; PostgreSQL in Docker for production-style execution.
- **Reliable ingestion**: SHA-256 content hashes make repeated imports idempotent. Documents are chunked and persisted transactionally.
- **Retrieval layer**: deterministic lexical cosine retrieval keeps the project runnable without external model/API credentials. The interface can later be replaced by embeddings without changing API contracts.
- **Structured extraction**: extracts case references, dates, euro amounts and email addresses into reviewable structured output.
- **Human-accountable AI pattern**: answers always return citations and `requires_human_review=true` rather than presenting generated text as authoritative legal advice.
- **Security boundary**: every case, document, chunk and audit event is tenant-scoped; API-key authentication demonstrates the isolation boundary.
- **Auditability**: create, ingest, search and answer events are recorded for traceability.

## Reliability decisions

1. Idempotent case creation by `(tenant_id, external_ref)`.
2. Idempotent document ingestion by `(tenant_id, content_hash)`.
3. Cross-tenant access returns 404 to avoid leaking resource existence.
4. Search and answer outputs include source IDs, chunk indices and excerpts.
5. Database constraints back application-level checks.

## Production extensions

A real deployment could swap API keys for OIDC, use S3 for raw documents, SQS/Celery for long-running OCR jobs, OpenSearch/pgvector for semantic retrieval, and AWS ECS/RDS for runtime infrastructure. These are documented as deployment options rather than falsely presented as implemented runtime dependencies.
