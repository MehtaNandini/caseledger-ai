from __future__ import annotations
import hashlib
import json
import math
import re
from collections import Counter
from sqlalchemy.orm import Session
from .models import AuditEvent, Chunk, Document

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9§€.-]+")

def normalize_tokens(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text) if len(t) > 1]

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def chunk_text(text: str, chunk_words: int = 180, overlap: int = 30) -> list[str]:
    words = text.split()
    if not words:
        return []
    out, start = [], 0
    step = max(1, chunk_words - overlap)
    while start < len(words):
        out.append(" ".join(words[start:start + chunk_words]))
        start += step
    return out

def similarity(query: str, text: str) -> float:
    q = Counter(normalize_tokens(query))
    d = Counter(normalize_tokens(text))
    if not q or not d:
        return 0.0
    dot = sum(q[k] * d.get(k, 0) for k in q)
    qn = math.sqrt(sum(v * v for v in q.values()))
    dn = math.sqrt(sum(v * v for v in d.values()))
    return dot / (qn * dn) if qn and dn else 0.0

def search_chunks(db: Session, tenant_id: int, case_id: int, query: str, limit: int = 5):
    chunks = (
        db.query(Chunk)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.tenant_id == tenant_id, Document.case_id == case_id)
        .all()
    )
    scored = [(similarity(query, c.text), c) for c in chunks]
    scored = [(s, c) for s, c in scored if s > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:limit]

def extract_structured_fields(text: str) -> dict:
    case_refs = re.findall(r"\b(?:IN|AZ|Case)\s*[A-Z0-9./-]{2,}\b", text, flags=re.IGNORECASE)
    euro_amounts = re.findall(r"\b\d{1,3}(?:[. ]\d{3})*(?:,\d{2})?\s*€", text)
    dates = re.findall(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", text)
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return {
        "case_references": sorted(set(case_refs))[:20],
        "euro_amounts": sorted(set(euro_amounts))[:20],
        "dates": sorted(set(dates))[:20],
        "emails": sorted(set(emails))[:20],
    }

def grounded_answer(question: str, hits: list[tuple[float, Chunk]]) -> dict:
    if not hits:
        return {"answer": "No sufficiently relevant case-file content was found.", "citations": [], "quality": {"grounded": True, "coverage": 0.0}}
    citations = []
    snippets = []
    for score, chunk in hits:
        excerpt = chunk.text[:360]
        snippets.append(excerpt)
        citations.append({
            "document_id": chunk.document_id,
            "chunk": chunk.ordinal,
            "score": round(score, 4),
            "excerpt": excerpt,
        })
    answer = "Based on the retrieved case-file content: " + " ".join(snippets[:3])
    return {
        "answer": answer,
        "citations": citations,
        "quality": {
            "grounded": bool(citations),
            "coverage": round(min(1.0, sum(c["score"] for c in citations[:3])), 4),
            "requires_human_review": True,
        },
        "question": question,
    }

def audit(db: Session, tenant_id: int, action: str, entity_type: str, entity_id: str, details: dict | None = None):
    db.add(AuditEvent(
        tenant_id=tenant_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=json.dumps(details or {}, ensure_ascii=False),
    ))
