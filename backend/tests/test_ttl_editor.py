"""
tests/test_ttl_editor.py — TTL 편집기 API 테스트 (§27-1 E1, E2)

엔드포인트:
  GET /ontologies/{id}/graphs/ttl?graph_iri=<IRI>  → Named Graph Turtle 반환
  PUT /ontologies/{id}/graphs/ttl?graph_iri=<IRI>  → Named Graph Turtle 교체
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

ONT_IRI = "https://test.example.org/ontology"
GRAPH_IRI = f"{ONT_IRI}/manual"
SAMPLE_TURTLE = b"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<http://ex.org/A> a owl:Class .\n"


# ── E1: GET TTL ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ttl_returns_turtle(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /graphs/ttl?graph_iri=... → 200 with Turtle content."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.export_turtle = AsyncMock(return_value=SAMPLE_TURTLE.decode())

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/turtle")
    assert b"owl:Class" in response.content
    store.export_turtle.assert_called_once_with(GRAPH_IRI, dataset=None)


@pytest.mark.asyncio
async def test_get_ttl_ontology_not_found(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /graphs/ttl → 404 when ontology not found."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=None):
        response = await client.get(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ONTOLOGY_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_ttl_missing_graph_iri(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /graphs/ttl without graph_iri → 422."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(f"/ontologies/{oid}/graphs/ttl")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_ttl_graph_not_in_ontology(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /graphs/ttl with graph_iri not under ontology prefix → 403."""
    oid = created_ontology["id"]

    foreign_graph = "https://other.example.org/graph"

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": foreign_graph},
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "GRAPH_NOT_IN_ONTOLOGY"


# ── E2: PUT TTL ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_put_ttl_replaces_graph(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT /graphs/ttl?graph_iri=... → 204 and calls put_graph_turtle."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.put_graph_turtle = AsyncMock(return_value=None)

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
            content=SAMPLE_TURTLE,
            headers={"Content-Type": "text/turtle"},
        )

    assert response.status_code == 204
    store.put_graph_turtle.assert_called_once_with(GRAPH_IRI, SAMPLE_TURTLE, dataset=None)


@pytest.mark.asyncio
async def test_put_ttl_ontology_not_found(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT /graphs/ttl → 404 when ontology not found."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=None):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
            content=SAMPLE_TURTLE,
            headers={"Content-Type": "text/turtle"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_put_ttl_graph_not_in_ontology(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT /graphs/ttl with foreign graph_iri → 403."""
    oid = created_ontology["id"]

    foreign_graph = "https://other.example.org/graph"

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": foreign_graph},
            content=SAMPLE_TURTLE,
            headers={"Content-Type": "text/turtle"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_put_ttl_invalid_content_type(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT /graphs/ttl with non-turtle content-type → 415."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
            content=b"not turtle",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 415
