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
    "parent_iris": [],
    "restrictions": [],
}


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
