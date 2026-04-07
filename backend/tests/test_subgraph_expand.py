"""
통합 테스트: 더블클릭 그래프 확장 — depth-1 서브그래프 API

시나리오:
  - A → B → C (체인 연결)
  - A에서 depth=1: A, B만 반환 (C 미포함)
  - B에서 depth=1: A, B, C 모두 반환 (B의 양방향 이웃)
  - 반환 노드에 이미 존재하는 IRI는 중복 없이 포함

검증:
  1. depth=1, seed=A → nodes에 A, B 포함, C 미포함
  2. depth=1, seed=B → nodes에 A, B, C 모두 포함
  3. edges에 A→B 엣지 포함 (seed=A, depth=1)
"""
from __future__ import annotations

import pytest
import httpx

BASE_URL = "http://localhost/api/v1"
ONT_BASE = "https://subgraph-expand-test.example.org/onto"

A = f"{ONT_BASE}#NodeA"
B = f"{ONT_BASE}#NodeB"
C = f"{ONT_BASE}#NodeC"
KNOWS = f"{ONT_BASE}#knows"


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        yield c


@pytest.fixture(scope="module")
def ontology(client):
    resp = client.post("/ontologies", json={
        "label": "Subgraph Expand Test",
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
    client.post(f"/ontologies/{oid}/concepts", json={"iri": f"{ONT_BASE}#Node", "label": "Node"})

    # Individual 생성
    for iri, label in [(A, "NodeA"), (B, "NodeB"), (C, "NodeC")]:
        r = client.post(f"/ontologies/{oid}/individuals", json={
            "iri": iri, "label": label, "types": [f"{ONT_BASE}#Node"],
        })
        assert r.status_code == 201, r.text

    # A → B → C 연결 (SPARQL INSERT)
    kg = f"{ONT_BASE}/kg"
    sparql_update = f"""
PREFIX : <{ONT_BASE}#>
INSERT DATA {{
  GRAPH <{kg}> {{
    :NodeA :knows :NodeB .
    :NodeB :knows :NodeC .
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


# ── 1. seed=A, depth=1 → B 포함, C 미포함 ────────────────────────────────────

def test_depth1_from_a_includes_b_not_c(client, ontology, setup):
    """A에서 depth=1 확장 시 B 포함, C 미포함."""
    oid = ontology["id"]
    resp = client.post(f"/ontologies/{oid}/subgraph", json={"entity_iris": [A], "depth": 1})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    node_iris = {n["iri"] for n in data["nodes"]}
    assert A in node_iris, f"A가 nodes에 없음: {node_iris}"
    assert B in node_iris, f"B가 nodes에 없음: {node_iris}"
    assert C not in node_iris, f"C가 nodes에 포함됨 (depth=1 위반): {node_iris}"


# ── 2. seed=B, depth=1 → A, B, C 모두 포함 ───────────────────────────────────

def test_depth1_from_b_includes_all(client, ontology, setup):
    """B에서 depth=1 확장 시 양방향 이웃(A, C) 모두 포함."""
    oid = ontology["id"]
    resp = client.post(f"/ontologies/{oid}/subgraph", json={"entity_iris": [B], "depth": 1})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    node_iris = {n["iri"] for n in data["nodes"]}
    assert A in node_iris, f"A가 nodes에 없음 (역방향 이웃): {node_iris}"
    assert B in node_iris, f"B가 nodes에 없음: {node_iris}"
    assert C in node_iris, f"C가 nodes에 없음 (순방향 이웃): {node_iris}"


# ── 3. seed=A, depth=1 → A→B 엣지 포함 ──────────────────────────────────────

def test_depth1_from_a_includes_edge(client, ontology, setup):
    """A에서 depth=1 확장 시 A→B 엣지(knows) 포함."""
    oid = ontology["id"]
    resp = client.post(f"/ontologies/{oid}/subgraph", json={"entity_iris": [A], "depth": 1})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    edges = data["edges"]
    found = any(e["source"] == A and e["target"] == B for e in edges)
    assert found, f"A→B 엣지가 edges에 없음: {edges}"
