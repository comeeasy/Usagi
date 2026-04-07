"""
통합 테스트: predicate 사용 기반 Property 추론

시나리오:
  - :knows   → owl:ObjectProperty 선언 없이 IRI 간 predicate로 사용
  - :age     → owl:DatatypeProperty 선언 없이 literal predicate로 사용
  - :worksFor → owl:ObjectProperty 명시 선언 (기존 방식)
  - rdf:type, rdfs:label → 시스템 predicate → 제외돼야 함

검증:
  1. kind=object → :knows, :worksFor 포함
  2. kind=data   → :age 포함
  3. rdf:type, rdfs:label 미포함
"""
from __future__ import annotations

import pytest
import httpx
from urllib.parse import quote

BASE_URL = "http://localhost/api/v1"
ONT_BASE = "https://prop-infer-test.example.org/onto"

PERSON   = f"{ONT_BASE}#Person"
ALICE    = f"{ONT_BASE}#Alice"
BOB      = f"{ONT_BASE}#Bob"
KNOWS    = f"{ONT_BASE}#knows"     # 선언 없이 IRI→IRI 사용
AGE      = f"{ONT_BASE}#age"       # 선언 없이 IRI→literal 사용
WORKS_FOR = f"{ONT_BASE}#worksFor" # owl:ObjectProperty 명시 선언


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def ontology(client):
    resp = client.post("/ontologies", json={
        "label": "Property Inference Test",
        "iri": ONT_BASE,
        "version": "1.0.0",
    })
    assert resp.status_code == 201, resp.text
    ont = resp.json()
    yield ont
    client.delete(f"/ontologies/{ont['id']}")


@pytest.fixture(scope="module")
def setup(client, ontology):
    oid = ontology["id"]

    # 클래스 생성
    client.post(f"/ontologies/{oid}/concepts", json={"iri": PERSON, "label": "Person"})

    # owl:ObjectProperty 명시 선언
    r = client.post(f"/ontologies/{oid}/properties", json={
        "iri": WORKS_FOR, "label": "worksFor",
        "kind": "object", "domain": [PERSON], "range": [PERSON],
    })
    assert r.status_code == 201, r.text

    # Individual + 선언 없는 predicate 사용 (SPARQL INSERT로 직접)
    kg = f"{ONT_BASE}/kg"
    sparql_update = f"""
PREFIX : <{ONT_BASE}#>
INSERT DATA {{
  GRAPH <{kg}> {{
    :{ALICE.split('#')[1]} a :{PERSON.split('#')[1]} ;
        :{KNOWS.split('#')[1]} :{BOB.split('#')[1]} ;
        :{AGE.split('#')[1]} 25 .
    :{BOB.split('#')[1]} a :{PERSON.split('#')[1]} .
  }}
}}"""
    r2 = httpx.post(
        "http://localhost:3030/ontology/update",
        content=sparql_update,
        headers={"Content-Type": "application/sparql-update"},
        auth=("admin", "admin"),
    )
    assert r2.status_code in (200, 204), r2.text

    return {"oid": oid}


# ── 1. Object Properties: 선언된 것 + predicate 추론 ────────────────────────

def test_object_properties_includes_undeclared_iri_predicate(client, ontology, setup):
    """:knows (선언 없음, IRI→IRI 사용) → kind=object 목록에 포함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/properties", params={"kind": "object", "page_size": 50})
    assert resp.status_code == 200, resp.text
    iris = {i["iri"] for i in resp.json()["items"]}
    assert KNOWS in iris,     f":knows가 object properties에 없음: {iris}"
    assert WORKS_FOR in iris, f":worksFor가 object properties에 없음: {iris}"


# ── 2. Data Properties: literal predicate 추론 ──────────────────────────────

def test_data_properties_includes_undeclared_literal_predicate(client, ontology, setup):
    """:age (선언 없음, IRI→literal 사용) → kind=data 목록에 포함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/properties", params={"kind": "data", "page_size": 50})
    assert resp.status_code == 200, resp.text
    iris = {i["iri"] for i in resp.json()["items"]}
    assert AGE in iris, f":age가 data properties에 없음: {iris}"


# ── 3. 시스템 predicate 제외 ─────────────────────────────────────────────────

def test_system_predicates_excluded(client, ontology, setup):
    """rdf:type, rdfs:label 등 시스템 predicate는 Relations에 미포함."""
    oid = ontology["id"]
    resp = client.get(f"/ontologies/{oid}/properties", params={"page_size": 100})
    iris = {i["iri"] for i in resp.json()["items"]}

    system = {
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://www.w3.org/2000/01/rdf-schema#subClassOf",
        "http://www.w3.org/2002/07/owl#Class",
    }
    found = iris & system
    assert not found, f"시스템 predicate가 Relations에 포함됨: {found}"
