"""
tests/test_properties_rdfs_literal.py

R1: DataProperty range에 rdfs:Literal이 있을 때 500 없이 조회되는지 검증.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


ONT_IRI = "https://test.example.org/ontology"


@pytest.mark.asyncio
async def test_list_data_properties_with_rdfs_literal_range_returns_200(
    client: AsyncClient, created_ontology: dict
) -> None:
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]

    # list_properties(kind=data) -> fetch_pattern(count, rows) + _fetch_data_property(basic/domain/range/superprops)
    store.sparql_select.side_effect = [
        [{"total": {"value": "1"}}],  # count
        [{"iri": {"value": "https://test.example.org/onto#description"}}],  # rows
        [{"label": {"value": "description"}, "comment": {"value": "desc"}}],  # basic
        [{"d": {"value": "https://test.example.org/onto#Person"}}],  # domain
        [{"r": {"value": "http://www.w3.org/2000/01/rdf-schema#Literal"}}],  # range (problematic)
        [],  # super properties
    ]
    store.sparql_ask.return_value = False  # is_functional

    with patch("api.properties.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(
            f"/ontologies/{oid}/properties",
            params={"kind": "data", "page": 1, "page_size": 50, "dataset": "ontology"},
        )

    # 기대 동작: rdfs:Literal이 있어도 500이 아니라 정상 응답이어야 한다.
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["range"][0] in ("xsd:langString", "rdfs:Literal")
