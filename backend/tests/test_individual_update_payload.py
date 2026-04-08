"""
tests/test_individual_update_payload.py

IBUG-1: Individual update payload에서 graph_iri 없이도 처리 가능한지 검증.
"""
from __future__ import annotations

from unittest.mock import patch
from urllib.parse import quote

import pytest
from httpx import AsyncClient


ONT_IRI = "https://test.example.org/ontology"
IND_IV = f"{ONT_IRI}#alice"


@pytest.mark.asyncio
async def test_update_individual_without_graph_iri_fields(
    client: AsyncClient, created_ontology: dict
) -> None:
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]

    # update_individual entry check + get_individual existence check
    store.sparql_ask.side_effect = [True, True]
    # get_individual triples query returns minimal row
    store.sparql_select.return_value = [
        {"p": {"value": "http://www.w3.org/2000/01/rdf-schema#label"}, "o": {"type": "literal", "value": "Alice"}}
    ]

    payload = {
        "label": "Alice Updated",
        "types": [f"{ONT_IRI}#Person"],
        "data_property_values": [
            {"property_iri": f"{ONT_IRI}#age", "value": "31", "datatype": "xsd:integer"}
        ],
        "object_property_values": [
            {"property_iri": f"{ONT_IRI}#worksFor", "target_iri": f"{ONT_IRI}#CompanyA"}
        ],
    }

    with patch("api.individuals.resolve_ontology_iri", return_value=ONT_IRI):
        resp = await client.put(
            f"/ontologies/{oid}/individuals/{quote(IND_IV, safe='')}",
            json=payload,
        )

    assert resp.status_code == 200, resp.text
