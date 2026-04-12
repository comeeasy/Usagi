"""
tests/test_graphs_ttl.py — Named Graph TTL 조회/교체 API 테스트 (Section 31)

T1: GET /graphs/ttl → 200, text/turtle 응답
T2: PUT /graphs/ttl (text/turtle) → 204
T3: PUT /graphs/ttl 잘못된 Content-Type → 415
T4: graph_iri가 ontology 소속 아닌 경우 → 403
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

ONT_IRI   = "https://test.example.org/ontology"
GRAPH_IRI = f"{ONT_IRI}/manual"
OTHER_IRI = "https://other.example.org/graph"

SAMPLE_TTL = (
    "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
    "<https://ex.org/A> a owl:Class .\n"
)


# ── T1: GET /graphs/ttl ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_graph_ttl_returns_turtle(
    client: AsyncClient, created_ontology: dict
) -> None:
    """GET /graphs/ttl?graph_iri=... → 200, text/turtle 반환."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.export_turtle = AsyncMock(return_value=SAMPLE_TTL)

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
        )

    assert response.status_code == 200, response.text
    assert "text/turtle" in response.headers["content-type"]
    assert "@prefix owl:" in response.text
    store.export_turtle.assert_awaited_once_with(GRAPH_IRI, dataset=None)


# ── T2: PUT /graphs/ttl ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_put_graph_ttl_returns_204(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT /graphs/ttl (Content-Type: text/turtle) → 204 No Content."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]
    store.put_graph_turtle = AsyncMock(return_value=None)

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
            content=SAMPLE_TTL.encode(),
            headers={"Content-Type": "text/turtle"},
        )

    assert response.status_code == 204, response.text
    store.put_graph_turtle.assert_awaited_once()
    call_args = store.put_graph_turtle.call_args
    assert call_args.args[0] == GRAPH_IRI


# ── T3: PUT 잘못된 Content-Type ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_put_graph_ttl_wrong_content_type_returns_415(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT /graphs/ttl with application/json → 415 Unsupported Media Type."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": GRAPH_IRI},
            content=b'{"bad": "json"}',
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 415, response.text
    assert response.json()["detail"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


# ── T4: graph_iri 소속 검증 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_graph_ttl_wrong_ownership_returns_403(
    client: AsyncClient, created_ontology: dict
) -> None:
    """graph_iri가 ontology IRI 하위가 아니면 → 403 Forbidden."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": OTHER_IRI},
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "GRAPH_NOT_IN_ONTOLOGY"


@pytest.mark.asyncio
async def test_put_graph_ttl_wrong_ownership_returns_403(
    client: AsyncClient, created_ontology: dict
) -> None:
    """PUT graph_iri가 ontology IRI 하위가 아니면 → 403 Forbidden."""
    oid = created_ontology["id"]

    with patch("api.graphs.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.put(
            f"/ontologies/{oid}/graphs/ttl",
            params={"graph_iri": OTHER_IRI},
            content=SAMPLE_TTL.encode(),
            headers={"Content-Type": "text/turtle"},
        )

    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "GRAPH_NOT_IN_ONTOLOGY"
