"""
Tests for /ontologies/{id}/concepts API endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


SAMPLE_CONCEPT = {
    "iri": "https://test.example.org/ontology#TestConcept",
    "label": "Test Concept",
    "comment": "A concept for testing",
    "parent_iris": [],
    "restrictions": [],
}


@pytest.mark.asyncio
async def test_create_concept(client: AsyncClient, sample_ontology: dict) -> None:
    """POST /ontologies/{id}/concepts → 201 Created."""
    # TODO: implement
    # create_ont = await client.post("/ontologies", json=sample_ontology)
    # oid = create_ont.json()["id"]
    # response = await client.post(f"/ontologies/{oid}/concepts", json=SAMPLE_CONCEPT)
    # assert response.status_code == 201
    # assert response.json()["iri"] == SAMPLE_CONCEPT["iri"]
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_list_concepts(client: AsyncClient, sample_ontology: dict) -> None:
    """GET /ontologies/{id}/concepts → 200."""
    # TODO: implement
    # create_ont = await client.post("/ontologies", json=sample_ontology)
    # oid = create_ont.json()["id"]
    # response = await client.get(f"/ontologies/{oid}/concepts")
    # assert response.status_code == 200
    # assert "items" in response.json()
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_get_concept(client: AsyncClient, sample_ontology: dict) -> None:
    """GET /ontologies/{id}/concepts/{iri} → 200."""
    # TODO: implement
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_update_concept(client: AsyncClient, sample_ontology: dict) -> None:
    """PUT /ontologies/{id}/concepts/{iri} → 200."""
    # TODO: implement
    pytest.skip("Not implemented yet")


@pytest.mark.asyncio
async def test_delete_concept(client: AsyncClient, sample_ontology: dict) -> None:
    """DELETE /ontologies/{id}/concepts/{iri} → 204."""
    # TODO: implement
    pytest.skip("Not implemented yet")
