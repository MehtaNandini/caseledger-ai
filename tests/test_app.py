import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, SessionLocal
from app.models import Tenant

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add_all([
            Tenant(name="Firm A", api_key="a-key"),
            Tenant(name="Firm B", api_key="b-key"),
        ])
        db.commit()
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def h(key="a-key"):
    return {"X-API-Key": key}

def create_case(key="a-key", ref="CASE-1"):
    r=client.post("/api/cases",headers=h(key),json={"external_ref":ref,"title":"Case title"})
    assert r.status_code==201
    return r.json()["id"]

def test_case_creation_is_idempotent():
    first=client.post("/api/cases",headers=h(),json={"external_ref":"CASE-1","title":"Title"})
    second=client.post("/api/cases",headers=h(),json={"external_ref":"CASE-1","title":"Title"})
    assert first.status_code==201 and second.status_code==201
    assert second.json()["idempotent_replay"] is True
    assert first.json()["id"]==second.json()["id"]

def test_document_ingestion_is_idempotent_and_extracts_fields():
    cid=create_case()
    payload={"filename":"notice.txt","text":"Case IN 142/26. Amount 23.450,80 €. Hearing 14.05.2026. Contact a@example.org."}
    one=client.post(f"/api/cases/{cid}/documents",headers=h(),json=payload)
    two=client.post(f"/api/cases/{cid}/documents",headers=h(),json=payload)
    assert one.status_code==201 and two.status_code==201
    assert two.json()["idempotent_replay"] is True
    assert "23.450,80 €" in one.json()["structured"]["euro_amounts"]
    assert "14.05.2026" in one.json()["structured"]["dates"]

def test_tenant_isolation():
    cid=create_case("a-key")
    forbidden=client.post(f"/api/cases/{cid}/search",headers=h("b-key"),json={"query":"anything"})
    assert forbidden.status_code==404

def test_grounded_answer_contains_citations_and_human_review_flag():
    cid=create_case()
    client.post(f"/api/cases/{cid}/documents",headers=h(),json={"filename":"claim.txt","text":"The claim amount is 18.000,00 € and the next hearing is on 22.06.2026."})
    r=client.post(f"/api/cases/{cid}/answer",headers=h(),json={"question":"What is the claim amount and hearing?"})
    body=r.json()
    assert r.status_code==200
    assert body["citations"]
    assert body["quality"]["grounded"] is True
    assert body["quality"]["requires_human_review"] is True

def test_audit_log_records_actions():
    cid=create_case()
    client.post(f"/api/cases/{cid}/documents",headers=h(),json={"filename":"x.txt","text":"Relevant legal file content."})
    r=client.get("/api/audit",headers=h())
    actions={x["action"] for x in r.json()}
    assert "case.created" in actions and "document.ingested" in actions

def test_invalid_api_key_rejected():
    r=client.get("/api/cases",headers=h("wrong"))
    assert r.status_code==401
