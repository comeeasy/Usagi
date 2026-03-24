"""
Tests for /ontologies API endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from urllib.parse import quote


@pytest.mark.asyncio
async def test_create_ontology(client: AsyncClient, sample_ontology: dict) -> None:
    """POST /ontologies → 201 Created."""
    response = await client.post("/ontologies", json=sample_ontology)
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == sample_ontology["label"]
    assert data["iri"] == sample_ontology["iri"]
    assert "id" in data


@pytest.mark.asyncio
async def test_create_ontology_duplicate_iri(client: AsyncClient, sample_ontology: dict) -> None:
    """POST /ontologies — 동일 IRI 두 번 → 409 Conflict."""
    await client.post("/ontologies", json=sample_ontology)
    response = await client.post("/ontologies", json=sample_ontology)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_ontologies_empty(client: AsyncClient) -> None:
    """GET /ontologies — 빈 상태 → 200 + items=[], total=0."""
    response = await client.get("/ontologies")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_ontologies_paginated(client: AsyncClient, sample_ontology: dict) -> None:
    """GET /ontologies — 온톨로지 생성 후 목록 조회."""
    await client.post("/ontologies", json=sample_ontology)
    response = await client.get("/ontologies")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["label"] == sample_ontology["label"]


@pytest.mark.asyncio
async def test_get_ontology(client: AsyncClient, created_ontology: dict) -> None:
    """GET /ontologies/{id} → 200."""
    ont_id = created_ontology["id"]
    response = await client.get(f"/ontologies/{ont_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ont_id
    assert "stats" in data


@pytest.mark.asyncio
async def test_get_ontology_not_found(client: AsyncClient) -> None:
    """GET /ontologies/{id} — 존재하지 않는 id → 404."""
    response = await client.get("/ontologies/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_ontology(client: AsyncClient, created_ontology: dict) -> None:
    """PUT /ontologies/{id} → 200, 변경 내용 반영."""
    ont_id = created_ontology["id"]
    response = await client.put(f"/ontologies/{ont_id}", json={
        "label": "Updated Label",
        "description": "Updated description",
    })
    assert response.status_code == 200
    assert response.json()["label"] == "Updated Label"


@pytest.mark.asyncio
async def test_delete_ontology(client: AsyncClient, created_ontology: dict) -> None:
    """DELETE /ontologies/{id} → 204, 이후 GET → 404."""
    ont_id = created_ontology["id"]
    del_response = await client.delete(f"/ontologies/{ont_id}")
    assert del_response.status_code == 204

    get_response = await client.get(f"/ontologies/{ont_id}")
    assert get_response.status_code == 404
