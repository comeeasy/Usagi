"""
Tests for /ontologies API endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_ontology(client: AsyncClient, sample_ontology: dict) -> None:
    """POST /ontologies → 201 Created."""
    # TODO: implement
    # response = await client.post("/ontologies", json=sample_ontology)
    # assert response.status_code == 201
    # data = response.json()
    # assert data["name"] == sample_ontology["name"]
    # assert "id" in data
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_list_ontologies(client: AsyncClient) -> None:
    """GET /ontologies → 200 + 페이지네이션."""
    # TODO: implement
    # response = await client.get("/ontologies")
    # assert response.status_code == 200
    # data = response.json()
    # assert "items" in data
    # assert "total" in data
    # assert "page" in data
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_get_ontology(client: AsyncClient, sample_ontology: dict) -> None:
    """GET /ontologies/{id} → 200."""
    # TODO: implement
    # create_response = await client.post("/ontologies", json=sample_ontology)
    # ontology_id = create_response.json()["id"]
    # response = await client.get(f"/ontologies/{ontology_id}")
    # assert response.status_code == 200
    # assert response.json()["id"] == ontology_id
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_update_ontology(client: AsyncClient, sample_ontology: dict) -> None:
    """PUT /ontologies/{id} → 200."""
    # TODO: implement
    # create_response = await client.post("/ontologies", json=sample_ontology)
    # ontology_id = create_response.json()["id"]
    # update_payload = {"name": "Updated Name", "description": "Updated description"}
    # response = await client.put(f"/ontologies/{ontology_id}", json=update_payload)
    # assert response.status_code == 200
    # assert response.json()["name"] == "Updated Name"
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_delete_ontology(client: AsyncClient, sample_ontology: dict) -> None:
    """DELETE /ontologies/{id} → 204."""
    # TODO: implement
    # create_response = await client.post("/ontologies", json=sample_ontology)
    # ontology_id = create_response.json()["id"]
    # response = await client.delete(f"/ontologies/{ontology_id}")
    # assert response.status_code == 204
    # get_response = await client.get(f"/ontologies/{ontology_id}")
    # assert get_response.status_code == 404
    pytest.skip("Not implemented yet")
