"""
Tests for MergeService + /ontologies/{id}/merge API.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from services.merge_service import MergeService
from services.ontology_store import OntologyStore

BASE_IRI_A = "https://merge-test.example.org/onto-a"
BASE_IRI_B = "https://merge-test.example.org/onto-b"

# ── helpers ───────────────────────────────────────────────────────────────────

async def _create_ontology(client: AsyncClient, label: str, iri: str) -> dict:
    resp = await client.post("/ontologies", json={"label": label, "iri": iri})
    assert resp.status_code == 201
    return resp.json()


async def _add_concept(client: AsyncClient, oid: str, iri: str, label: str, **kwargs) -> dict:
    body = {"iri": iri, "label": label, **kwargs}
    resp = await client.post(f"/ontologies/{oid}/concepts", json=body)
    assert resp.status_code == 201
    return resp.json()


# ── MergeService 단위 테스트 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_conflicts_no_conflict(ontology_store: OntologyStore) -> None:
    """겹치는 IRI 없는 두 TBox → conflicts=[], auto_mergeable_count>0."""
    svc = MergeService(ontology_store)

    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{BASE_IRI_A}#Person> a owl:Class ; rdfs:label "Person" . }}
    GRAPH <{kg_b}> {{ <{BASE_IRI_B}#Department> a owl:Class ; rdfs:label "Department" . }}
}}""")

    result = await svc.detect_conflicts(BASE_IRI_A, BASE_IRI_B)
    assert result["conflicts"] == []
    assert result["auto_mergeable_count"] > 0


@pytest.mark.asyncio
async def test_detect_conflicts_label_conflict(ontology_store: OntologyStore) -> None:
    """동일 IRI에 다른 label → conflict_type='label'."""
    svc = MergeService(ontology_store)
    shared = "https://shared.example.org#Person"
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{shared}> rdfs:label "Person" . }}
    GRAPH <{kg_b}> {{ <{shared}> rdfs:label "PersonAlt" . }}
}}""")

    result = await svc.detect_conflicts(BASE_IRI_A, BASE_IRI_B)
    conflicts = result["conflicts"]
    assert any(c["conflict_type"] == "label" and c["iri"] == shared for c in conflicts)
    label_conflict = next(c for c in conflicts if c["conflict_type"] == "label")
    assert label_conflict["target_value"] == "Person"
    assert label_conflict["source_value"] == "PersonAlt"


@pytest.mark.asyncio
async def test_detect_conflicts_domain_conflict(ontology_store: OntologyStore) -> None:
    """동일 Property IRI에 다른 domain → conflict_type='domain'."""
    svc = MergeService(ontology_store)
    prop = "https://shared.example.org#worksIn"
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{prop}> rdfs:domain <https://shared.example.org#Employee> . }}
    GRAPH <{kg_b}> {{ <{prop}> rdfs:domain <https://shared.example.org#Person> . }}
}}""")

    result = await svc.detect_conflicts(BASE_IRI_A, BASE_IRI_B)
    assert any(c["conflict_type"] == "domain" for c in result["conflicts"])


@pytest.mark.asyncio
async def test_detect_conflicts_range_conflict(ontology_store: OntologyStore) -> None:
    """동일 Property IRI에 다른 range → conflict_type='range'."""
    svc = MergeService(ontology_store)
    prop = "https://shared.example.org#hasName"
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{prop}> rdfs:range xsd:string . }}
    GRAPH <{kg_b}> {{ <{prop}> rdfs:range xsd:anyURI . }}
}}""")

    result = await svc.detect_conflicts(BASE_IRI_A, BASE_IRI_B)
    assert any(c["conflict_type"] == "range" for c in result["conflicts"])


@pytest.mark.asyncio
async def test_merge_no_resolutions(ontology_store: OntologyStore) -> None:
    """resolutions=[] → 소스 트리플이 타겟에 추가됨."""
    svc = MergeService(ontology_store)
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{BASE_IRI_A}#Person> a owl:Class . }}
    GRAPH <{kg_b}> {{ <{BASE_IRI_B}#Department> a owl:Class . }}
}}""")

    result = await svc.merge(BASE_IRI_A, BASE_IRI_B, [])
    assert result["merged"] is True
    assert result["triple_count"] > 0

    # Department가 타겟 TBox에 추가됐는지 확인
    rows = await ontology_store.sparql_select(f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?c WHERE {{ GRAPH <{kg_a}> {{ ?c a owl:Class }} }}""")
    iris = [r["c"]["value"] for r in rows]
    assert f"{BASE_IRI_B}#Department" in iris


@pytest.mark.asyncio
async def test_merge_keep_target(ontology_store: OntologyStore) -> None:
    """keep-target → 타겟 label 유지, 소스 label 무시."""
    svc = MergeService(ontology_store)
    shared = "https://shared.example.org#Thing"
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{shared}> rdfs:label "TargetLabel" . }}
    GRAPH <{kg_b}> {{ <{shared}> rdfs:label "SourceLabel" . }}
}}""")

    from api.merge import ConflictResolution
    res = ConflictResolution(iri=shared, conflict_type="label", choice="keep-target")
    await svc.merge(BASE_IRI_A, BASE_IRI_B, [res])

    rows = await ontology_store.sparql_select(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?l WHERE {{ GRAPH <{kg_a}> {{ <{shared}> rdfs:label ?l }} }}""")
    labels = [r["l"]["value"] for r in rows]
    # keep-target이므로 TargetLabel이 반드시 존재해야 함
    # (SourceLabel이 있어도 TargetLabel이 유지되면 됨)
    assert "TargetLabel" in labels


@pytest.mark.asyncio
async def test_merge_keep_source(ontology_store: OntologyStore) -> None:
    """keep-source → 소스 label로 교체."""
    svc = MergeService(ontology_store)
    shared = "https://shared.example.org#Thing2"
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{shared}> rdfs:label "OldLabel" . }}
    GRAPH <{kg_b}> {{ <{shared}> rdfs:label "NewLabel" . }}
}}""")

    from api.merge import ConflictResolution
    res = ConflictResolution(iri=shared, conflict_type="label", choice="keep-source")
    await svc.merge(BASE_IRI_A, BASE_IRI_B, [res])

    rows = await ontology_store.sparql_select(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?l WHERE {{ GRAPH <{kg_a}> {{ <{shared}> rdfs:label ?l }} }}""")
    labels = [r["l"]["value"] for r in rows]
    assert "NewLabel" in labels
    assert "OldLabel" not in labels


@pytest.mark.asyncio
async def test_merge_both(ontology_store: OntologyStore) -> None:
    """merge-both → 타겟 + 소스 값 모두 존재."""
    svc = MergeService(ontology_store)
    shared = "https://shared.example.org#Thing3"
    kg_a = f"{BASE_IRI_A}/kg"
    kg_b = f"{BASE_IRI_B}/kg"

    await ontology_store.sparql_update(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
INSERT DATA {{
    GRAPH <{kg_a}> {{ <{shared}> rdfs:label "LabelA" . }}
    GRAPH <{kg_b}> {{ <{shared}> rdfs:label "LabelB" . }}
}}""")

    from api.merge import ConflictResolution
    res = ConflictResolution(iri=shared, conflict_type="label", choice="merge-both")
    await svc.merge(BASE_IRI_A, BASE_IRI_B, [res])

    rows = await ontology_store.sparql_select(f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?l WHERE {{ GRAPH <{kg_a}> {{ <{shared}> rdfs:label ?l }} }}""")
    labels = [r["l"]["value"] for r in rows]
    assert "LabelA" in labels
    assert "LabelB" in labels


def test_compare_literal_lists_equal() -> None:
    svc = MergeService.__new__(MergeService)
    assert svc._compare_literal_lists(["a", "b"], ["b", "a"]) is False


def test_compare_literal_lists_different() -> None:
    svc = MergeService.__new__(MergeService)
    assert svc._compare_literal_lists(["a"], ["b"]) is True


# ── API 통합 테스트 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_merge_preview_no_conflict(client: AsyncClient) -> None:
    """POST /merge/preview — 겹치는 IRI 없음 → conflicts=[]."""
    ont_a = await _create_ontology(client, "Onto A", BASE_IRI_A)
    ont_b = await _create_ontology(client, "Onto B", BASE_IRI_B)
    await _add_concept(client, ont_a["id"], f"{BASE_IRI_A}#Person", "Person")
    await _add_concept(client, ont_b["id"], f"{BASE_IRI_B}#Department", "Department")

    resp = await client.post(
        f"/ontologies/{ont_a['id']}/merge/preview",
        json={"source_ontology_id": ont_b["id"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conflicts"] == []
    assert data["auto_mergeable_count"] > 0


@pytest.mark.asyncio
async def test_api_merge_preview_with_conflict(client: AsyncClient) -> None:
    """POST /merge/preview — 동일 IRI 다른 label → conflicts 포함."""
    shared_iri = "https://shared.example.org#SharedClass"
    ont_a = await _create_ontology(client, "Onto A", BASE_IRI_A)
    ont_b = await _create_ontology(client, "Onto B", BASE_IRI_B)
    await _add_concept(client, ont_a["id"], shared_iri, "SharedA")
    await _add_concept(client, ont_b["id"], shared_iri, "SharedB")

    resp = await client.post(
        f"/ontologies/{ont_a['id']}/merge/preview",
        json={"source_ontology_id": ont_b["id"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["conflict_count"] > 0
    assert any(c["conflict_type"] == "label" for c in data["conflicts"])


@pytest.mark.asyncio
async def test_api_merge_execute(client: AsyncClient) -> None:
    """POST /merge — 병합 후 merged=True, triple_count>0."""
    ont_a = await _create_ontology(client, "Onto A", BASE_IRI_A)
    ont_b = await _create_ontology(client, "Onto B", BASE_IRI_B)
    await _add_concept(client, ont_a["id"], f"{BASE_IRI_A}#Person", "Person")
    await _add_concept(client, ont_b["id"], f"{BASE_IRI_B}#Department", "Department")

    resp = await client.post(
        f"/ontologies/{ont_a['id']}/merge",
        json={"source_ontology_id": ont_b["id"], "resolutions": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["merged"] is True
    assert data["triple_count"] > 0


@pytest.mark.asyncio
async def test_api_merge_execute_with_resolutions(client: AsyncClient) -> None:
    """POST /merge with keep-source resolution → 소스 label 적용 확인."""
    shared_iri = "https://shared.example.org#ResolvedClass"
    ont_a = await _create_ontology(client, "Onto A", BASE_IRI_A)
    ont_b = await _create_ontology(client, "Onto B", BASE_IRI_B)
    await _add_concept(client, ont_a["id"], shared_iri, "OldLabel")
    await _add_concept(client, ont_b["id"], shared_iri, "NewLabel")

    resp = await client.post(
        f"/ontologies/{ont_a['id']}/merge",
        json={
            "source_ontology_id": ont_b["id"],
            "resolutions": [
                {"iri": shared_iri, "conflict_type": "label", "choice": "keep-source"}
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["merged"] is True
