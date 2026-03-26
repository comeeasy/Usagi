"""
Tests for /ontologies/{id}/concepts API endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from urllib.parse import quote


SAMPLE_CONCEPT = {
    "iri": "https://test.example.org/ontology#TestConcept",
    "label": "Test Concept",
    "comment": "A concept for testing",
    "super_classes": [],
    "restrictions": [],
}

BASE = "https://test.example.org/ontology"


@pytest.mark.asyncio
async def test_create_concept(client: AsyncClient, created_ontology: dict) -> None:
    """POST /ontologies/{id}/concepts → 201 Created."""
    oid = created_ontology["id"]
    response = await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    assert response.status_code == 201
    data = response.json()
    assert data["iri"] == SAMPLE_CONCEPT["iri"]
    assert data["label"] == SAMPLE_CONCEPT["label"]


@pytest.mark.asyncio
async def test_create_concept_duplicate(client: AsyncClient, created_ontology: dict) -> None:
    """POST /ontologies/{id}/concepts — 동일 IRI 두 번 → 409."""
    oid = created_ontology["id"]
    await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    response = await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_concepts_empty(client: AsyncClient, created_ontology: dict) -> None:
    """GET /ontologies/{id}/concepts — 빈 상태 → items=[]."""
    oid = created_ontology["id"]
    response = await client.get(f"/ontologies/{oid}/concepts")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_concepts(client: AsyncClient, created_ontology: dict) -> None:
    """GET /ontologies/{id}/concepts — 생성 후 목록 조회."""
    oid = created_ontology["id"]
    await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    response = await client.get(f"/ontologies/{oid}/concepts")
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_concepts_search(client: AsyncClient, created_ontology: dict) -> None:
    """GET /ontologies/{id}/concepts?search=Test → 라벨 필터."""
    oid = created_ontology["id"]
    await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)

    response = await client.get(f"/ontologies/{oid}/concepts?search=Test")
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    response_no_match = await client.get(f"/ontologies/{oid}/concepts?search=XYZ_NOMATCH")
    assert response_no_match.status_code == 200
    assert response_no_match.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_concept(client: AsyncClient, created_ontology: dict) -> None:
    """GET /ontologies/{id}/concepts/{iri} → 200."""
    oid = created_ontology["id"]
    await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    encoded_iri = quote(SAMPLE_CONCEPT["iri"], safe="")
    response = await client.get(f"/ontologies/{oid}/concepts/{encoded_iri}")
    assert response.status_code == 200
    assert response.json()["iri"] == SAMPLE_CONCEPT["iri"]


@pytest.mark.asyncio
async def test_update_concept(client: AsyncClient, created_ontology: dict) -> None:
    """PUT /ontologies/{id}/concepts/{iri} → 200, 변경 반영."""
    oid = created_ontology["id"]
    await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    encoded_iri = quote(SAMPLE_CONCEPT["iri"], safe="")
    response = await client.put(
        f"/ontologies/{oid}/concepts/{encoded_iri}",
        json={"label": "Updated Concept", "comment": "Updated comment"},
    )
    assert response.status_code == 200
    assert response.json()["label"] == "Updated Concept"


@pytest.mark.asyncio
async def test_delete_concept(client: AsyncClient, created_ontology: dict) -> None:
    """DELETE /ontologies/{id}/concepts/{iri} → 204, 이후 GET → 404."""
    oid = created_ontology["id"]
    await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    encoded_iri = quote(SAMPLE_CONCEPT["iri"], safe="")

    del_response = await client.delete(f"/ontologies/{oid}/concepts/{encoded_iri}")
    assert del_response.status_code == 204

    get_response = await client.get(f"/ontologies/{oid}/concepts/{encoded_iri}")
    assert get_response.status_code == 404


# ── 고급 필드 테스트 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_concept_with_equivalent_class(client: AsyncClient, created_ontology: dict) -> None:
    """equivalent_classes 포함 생성 → GET 시 반환."""
    oid = created_ontology["id"]
    iri = f"{BASE}#ConceptA"
    eq_iri = f"{BASE}#ConceptB"
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": eq_iri, "label": "B"})
    resp = await client.post(f"/ontologies/{oid}/concepts", json={
        "iri": iri, "label": "A", "equivalent_classes": [eq_iri],
    })
    assert resp.status_code == 201

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{quote(iri, safe='')}")
    assert get_resp.status_code == 200
    assert eq_iri in get_resp.json()["equivalent_classes"]


@pytest.mark.asyncio
async def test_create_concept_with_disjoint_with(client: AsyncClient, created_ontology: dict) -> None:
    """disjoint_with 포함 생성 → GET 시 반환."""
    oid = created_ontology["id"]
    iri = f"{BASE}#Cat"
    dj_iri = f"{BASE}#Dog"
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": dj_iri, "label": "Dog"})
    resp = await client.post(f"/ontologies/{oid}/concepts", json={
        "iri": iri, "label": "Cat", "disjoint_with": [dj_iri],
    })
    assert resp.status_code == 201

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{quote(iri, safe='')}")
    assert get_resp.status_code == 200
    assert dj_iri in get_resp.json()["disjoint_with"]


@pytest.mark.asyncio
async def test_create_concept_with_some_restriction(client: AsyncClient, created_ontology: dict) -> None:
    """someValuesFrom restriction 포함 생성 → GET 시 restrictions 반환."""
    oid = created_ontology["id"]
    iri = f"{BASE}#Employee"
    restriction = {
        "property_iri": f"{BASE}#worksIn",
        "type": "someValuesFrom",
        "value": f"{BASE}#Department",
    }
    resp = await client.post(f"/ontologies/{oid}/concepts", json={
        "iri": iri, "label": "Employee", "restrictions": [restriction],
    })
    assert resp.status_code == 201

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{quote(iri, safe='')}")
    data = get_resp.json()
    assert len(data["restrictions"]) == 1
    r = data["restrictions"][0]
    assert r["type"] == "someValuesFrom"
    assert r["property_iri"] == restriction["property_iri"]


@pytest.mark.asyncio
async def test_create_concept_with_cardinality_restriction(client: AsyncClient, created_ontology: dict) -> None:
    """minCardinality restriction + cardinality → GET 시 cardinality 반환."""
    oid = created_ontology["id"]
    iri = f"{BASE}#Manager"
    restriction = {
        "property_iri": f"{BASE}#manages",
        "type": "minCardinality",
        "value": f"{BASE}#Employee",
        "cardinality": 1,
    }
    resp = await client.post(f"/ontologies/{oid}/concepts", json={
        "iri": iri, "label": "Manager", "restrictions": [restriction],
    })
    assert resp.status_code == 201

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{quote(iri, safe='')}")
    r = get_resp.json()["restrictions"][0]
    assert r["type"] == "minCardinality"
    assert r["cardinality"] == 1


@pytest.mark.asyncio
async def test_update_concept_equivalent_classes(client: AsyncClient, created_ontology: dict) -> None:
    """PUT → equivalent_classes 변경 반영."""
    oid = created_ontology["id"]
    iri = f"{BASE}#UpdateEq"
    eq1 = f"{BASE}#EqTarget"
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": eq1, "label": "EqTarget"})
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": iri, "label": "UpdateEq"})

    encoded = quote(iri, safe="")
    put_resp = await client.put(f"/ontologies/{oid}/concepts/{encoded}", json={"equivalent_classes": [eq1]})
    assert put_resp.status_code == 200

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{encoded}")
    assert eq1 in get_resp.json()["equivalent_classes"]


@pytest.mark.asyncio
async def test_update_concept_disjoint_with(client: AsyncClient, created_ontology: dict) -> None:
    """PUT → disjoint_with 변경 반영."""
    oid = created_ontology["id"]
    iri = f"{BASE}#UpdateDj"
    dj1 = f"{BASE}#DjTarget"
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": dj1, "label": "DjTarget"})
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": iri, "label": "UpdateDj"})

    encoded = quote(iri, safe="")
    put_resp = await client.put(f"/ontologies/{oid}/concepts/{encoded}", json={"disjoint_with": [dj1]})
    assert put_resp.status_code == 200

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{encoded}")
    assert dj1 in get_resp.json()["disjoint_with"]


@pytest.mark.asyncio
async def test_update_concept_restrictions(client: AsyncClient, created_ontology: dict) -> None:
    """PUT → restrictions 교체."""
    oid = created_ontology["id"]
    iri = f"{BASE}#UpdateRestr"
    await client.post(f"/ontologies/{oid}/concepts", json={"iri": iri, "label": "UpdateRestr"})

    new_restriction = {
        "property_iri": f"{BASE}#hasPart",
        "type": "allValuesFrom",
        "value": f"{BASE}#Part",
    }
    encoded = quote(iri, safe="")
    put_resp = await client.put(f"/ontologies/{oid}/concepts/{encoded}", json={"restrictions": [new_restriction]})
    assert put_resp.status_code == 200

    get_resp = await client.get(f"/ontologies/{oid}/concepts/{encoded}")
    restr = get_resp.json()["restrictions"]
    assert len(restr) == 1
    assert restr[0]["type"] == "allValuesFrom"
