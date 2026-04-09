"""
tests/test_concept_detail_fields.py — get_concept subclass_count / is_deprecated 필드 테스트

C30-1~C30-3 구현 검증:
  - subclass_count: rdfs:subClassOf <iri> 를 가진 직계 하위 클래스 수 반환
  - is_deprecated: owl:deprecated "true"^^xsd:boolean 트리플 존재 시 True 반환

패턴: resolve_ontology_iri patch + store.sparql_ask/select mock
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch
from urllib.parse import quote

ONT_IRI = "https://test.example.org/ontology"
CLASS_IRI = f"{ONT_IRI}#PersonConcept"


def _make_iri(value: str) -> dict:
    return {"type": "uri", "value": value}


def _make_lit(value: str, datatype: str | None = None) -> dict:
    d: dict = {"type": "literal", "value": value}
    if datatype:
        d["datatype"] = datatype
    return d


def _make_cnt(n: int) -> list[dict]:
    return [{"cnt": _make_lit(str(n), "http://www.w3.org/2001/XMLSchema#integer")}]


# ── subclass_count ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_concept_subclass_count(client: AsyncClient, created_ontology: dict) -> None:
    """get_concept → subclass_count가 직계 하위 클래스 수를 반환한다."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]

    store.sparql_ask.return_value = True

    # sparql_select 호출 순서: triples, restrictions, individual_cnt, subclass_cnt
    triples_result = [
        {"p": _make_iri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
         "o": _make_iri("http://www.w3.org/2002/07/owl#Class")},
        {"p": _make_iri("http://www.w3.org/2000/01/rdf-schema#label"),
         "o": _make_lit("PersonConcept")},
    ]
    rest_result: list[dict] = []
    ind_cnt_result = _make_cnt(2)
    sub_cnt_result = _make_cnt(3)

    store.sparql_select.side_effect = [
        triples_result,
        rest_result,
        ind_cnt_result,
        sub_cnt_result,
    ]

    encoded = quote(CLASS_IRI, safe="")
    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(f"/ontologies/{oid}/concepts/{encoded}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["subclass_count"] == 3, (
        f"subclass_count 기대 3, 실제 {data['subclass_count']}"
    )
    assert data["individual_count"] == 2, (
        f"individual_count 기대 2, 실제 {data['individual_count']}"
    )


@pytest.mark.asyncio
async def test_get_concept_subclass_count_zero(client: AsyncClient, created_ontology: dict) -> None:
    """get_concept → 하위 클래스 없는 leaf class는 subclass_count == 0."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]

    store.sparql_ask.return_value = True
    store.sparql_select.side_effect = [
        [{"p": _make_iri("http://www.w3.org/2000/01/rdf-schema#label"), "o": _make_lit("Leaf")}],
        [],
        _make_cnt(0),
        _make_cnt(0),
    ]

    encoded = quote(CLASS_IRI, safe="")
    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(f"/ontologies/{oid}/concepts/{encoded}")

    assert response.status_code == 200
    assert response.json()["subclass_count"] == 0


# ── is_deprecated ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_concept_is_deprecated_true(client: AsyncClient, created_ontology: dict) -> None:
    """owl:deprecated true 트리플 → is_deprecated == True."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]

    store.sparql_ask.return_value = True

    triples_result = [
        {"p": _make_iri("http://www.w3.org/2000/01/rdf-schema#label"),
         "o": _make_lit("OldConcept")},
        {"p": _make_iri("http://www.w3.org/2002/07/owl#deprecated"),
         "o": _make_lit("true", "http://www.w3.org/2001/XMLSchema#boolean")},
    ]

    store.sparql_select.side_effect = [
        triples_result,
        [],
        _make_cnt(0),
        _make_cnt(0),
    ]

    encoded = quote(CLASS_IRI, safe="")
    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(f"/ontologies/{oid}/concepts/{encoded}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["is_deprecated"] is True, (
        f"is_deprecated 기대 True, 실제 {data['is_deprecated']}"
    )


@pytest.mark.asyncio
async def test_get_concept_is_deprecated_false_by_default(
    client: AsyncClient, created_ontology: dict
) -> None:
    """owl:deprecated 트리플 없음 → is_deprecated == False."""
    oid = created_ontology["id"]
    store = client._transport.app.state.ontology_store  # type: ignore[attr-defined]

    store.sparql_ask.return_value = True
    store.sparql_select.side_effect = [
        [{"p": _make_iri("http://www.w3.org/2000/01/rdf-schema#label"), "o": _make_lit("ActiveConcept")}],
        [],
        _make_cnt(0),
        _make_cnt(0),
    ]

    encoded = quote(CLASS_IRI, safe="")
    with patch("api.concepts.resolve_ontology_iri", return_value=ONT_IRI):
        response = await client.get(f"/ontologies/{oid}/concepts/{encoded}")

    assert response.status_code == 200
    assert response.json()["is_deprecated"] is False
