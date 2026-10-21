from __future__ import annotations
import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .db import get_db, init_db
from .models import Case, Chunk, Document, Tenant, AuditEvent
from .schemas import CaseCreate, DocumentCreate, SearchRequest, SummaryRequest
from .services import audit, chunk_text, content_hash, extract_structured_fields, grounded_answer, search_chunks

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="CaseLedger AI", version="1.0.0", description="Multi-tenant case-file intelligence workspace with reliable ingestion, retrieval, structured extraction, and auditability.", lifespan=lifespan)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def tenant_from_key(x_api_key: str = Header(default=""), db: Session = Depends(get_db)) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.api_key == x_api_key).first()
    if not tenant:
        raise HTTPException(status_code=401, detail={"code": "invalid_api_key", "message": "Provide a valid X-API-Key."})
    return tenant

def tenant_case(db: Session, tenant_id: int, case_id: int) -> Case:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "case_not_found", "message": "Case not found for this tenant."})
    return case

@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/cases")
def list_cases(tenant: Tenant = Depends(tenant_from_key), db: Session = Depends(get_db)):
    rows = db.query(Case).filter(Case.tenant_id == tenant.id).order_by(Case.id.desc()).all()
    return [{"id": r.id, "external_ref": r.external_ref, "title": r.title, "status": r.status} for r in rows]

@app.post("/api/cases", status_code=201)
def create_case(payload: CaseCreate, tenant: Tenant = Depends(tenant_from_key), db: Session = Depends(get_db)):
    row = Case(tenant_id=tenant.id, external_ref=payload.external_ref, title=payload.title)
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Case).filter(Case.tenant_id == tenant.id, Case.external_ref == payload.external_ref).first()
        return {"id": existing.id, "external_ref": existing.external_ref, "title": existing.title, "status": existing.status, "idempotent_replay": True}
    audit(db, tenant.id, "case.created", "case", str(row.id), {"external_ref": row.external_ref})
    db.commit()
    return {"id": row.id, "external_ref": row.external_ref, "title": row.title, "status": row.status, "idempotent_replay": False}

@app.post("/api/cases/{case_id}/documents", status_code=201)
def add_document(case_id: int, payload: DocumentCreate, tenant: Tenant = Depends(tenant_from_key), db: Session = Depends(get_db)):
    tenant_case(db, tenant.id, case_id)
    digest = content_hash(payload.text)
    existing = db.query(Document).filter(Document.tenant_id == tenant.id, Document.content_hash == digest).first()
    if existing:
        if existing.case_id != case_id:
            raise HTTPException(status_code=409, detail={"code": "duplicate_document_other_case", "message": "Identical content already belongs to another case in this tenant."})
        return {"document_id": existing.id, "chunks": len(existing.chunks), "idempotent_replay": True, "structured": extract_structured_fields(existing.raw_text)}
    doc = Document(tenant_id=tenant.id, case_id=case_id, filename=payload.filename, content_hash=digest, raw_text=payload.text)
    db.add(doc)
    db.flush()
    parts = chunk_text(payload.text)
    for ordinal, text in enumerate(parts):
        db.add(Chunk(tenant_id=tenant.id, document_id=doc.id, ordinal=ordinal, text=text))
    audit(db, tenant.id, "document.ingested", "document", str(doc.id), {"case_id": case_id, "filename": payload.filename, "chunks": len(parts)})
    db.commit()
    return {"document_id": doc.id, "chunks": len(parts), "idempotent_replay": False, "structured": extract_structured_fields(payload.text)}

@app.post("/api/cases/{case_id}/search")
def search(case_id: int, payload: SearchRequest, tenant: Tenant = Depends(tenant_from_key), db: Session = Depends(get_db)):
    tenant_case(db, tenant.id, case_id)
    hits = search_chunks(db, tenant.id, case_id, payload.query, payload.limit)
    audit(db, tenant.id, "case.searched", "case", str(case_id), {"query": payload.query, "hits": len(hits)})
    db.commit()
    return [{"score": round(score, 4), "document_id": c.document_id, "chunk": c.ordinal, "text": c.text} for score, c in hits]

@app.post("/api/cases/{case_id}/answer")
def answer(case_id: int, payload: SummaryRequest, tenant: Tenant = Depends(tenant_from_key), db: Session = Depends(get_db)):
    tenant_case(db, tenant.id, case_id)
    hits = search_chunks(db, tenant.id, case_id, payload.question, payload.limit)
    result = grounded_answer(payload.question, hits)
    audit(db, tenant.id, "case.answer_generated", "case", str(case_id), {"question": payload.question, "citations": len(result["citations"])})
    db.commit()
    return result

@app.get("/api/audit")
def audit_log(tenant: Tenant = Depends(tenant_from_key), db: Session = Depends(get_db)):
    rows = db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant.id).order_by(AuditEvent.id.desc()).limit(100).all()
    return [{"id": r.id, "action": r.action, "entity_type": r.entity_type, "entity_id": r.entity_id, "details": json.loads(r.details), "created_at": r.created_at.isoformat()} for r in rows]
