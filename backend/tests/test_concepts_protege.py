"""
Section 25: Protege 방식 클래스 리스팅 검증 테스트

검증 항목:
1. ABox 노이즈 패턴(`[] rdf:type ?iri`) 미사용
2. TBox 명시 선언 패턴만 사용 (owl:Class, rdfs:Class, skos:Concept, subClassOf, domain/range)
3. skos:prefLabel 폴백 레이블 반환
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, call
from httpx import AsyncClient

ONT_IRI = "https://test.example.org/ontology"
ONT_UUID = "test-uuid-0001"

# _resolve_ont 가 반환할 응답
_RESOLVE_ROWS = [{"iri": {"value": ONT_IRI}}]
# 빈 count
_COUNT_ZERO = [{"total": {"value": "0"}}]
# concept 1건
_CONCEPT_ROW = [{
    "iri": {"value": f"{ONT_IRI}#Animal"},
    "label": {"value": "Animal"},
    "comment": None,
    "subclassCount": {"value": "0"},
    "individualCount": {"value": "0"},
}]
# skos:prefLabel 만 있는 concept
_CONCEPT_SKOS_ROW = [{
    "iri": {"value": f"{ONT_IRI}#Plant"},
    "label": {"value": "Plant"},   # COALESCE(rdfs:label, skos:prefLabel)
    "comment": None,
    "subclassCount": {"value": "0"},
    "individualCount": {"value": "0"},
}]


def _make_side_effect(*per_call):
    """순서대로 다른 값을 반환하는 side_effect 생성."""
    it = iter(per_call)
    async def _se(*args, **kwargs):
        return next(it)
    return _se


# ── 테스트 1: ABox 노이즈 패턴 미사용 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_concepts_no_abox_noise_pattern(
    client: AsyncClient, ontology_store: AsyncMock, created_ontology: dict
) -> None:
    """list_concepts SPARQL에 '[] rdf:type ?iri' ABox 노이즈 패턴이 없어야 한다."""
    oid = created_ontology["id"]

    ontology_store.sparql_select.side_effect = _make_side_effect(
        _RESOLVE_ROWS,   # _resolve_ont
        _COUNT_ZERO,     # COUNT 쿼리
        [],              # items 쿼리
    )

    resp = await client.get(f"/ontologies/{oid}/concepts")
    assert resp.status_code == 200

    # sparql_select 에 전달된 SPARQL 문자열 수집
    all_sparql = " ".join(
        str(c.args[0]) for c in ontology_store.sparql_select.call_args_list
    )

    # ABox 노이즈 패턴 미포함 검증
    assert "[] rdf:type ?iri" not in all_sparql, (
        "ABox 노이즈 패턴 '[] rdf:type ?iri' 가 SPARQL에 포함되어 있음"
    )


# ── 테스트 2: TBox 패턴 포함 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_concepts_contains_tbox_patterns(
    client: AsyncClient, ontology_store: AsyncMock, created_ontology: dict
) -> None:
    """list_concepts SPARQL에 TBox 명시 선언 패턴이 포함되어야 한다."""
    oid = created_ontology["id"]

    ontology_store.sparql_select.side_effect = _make_side_effect(
        _RESOLVE_ROWS,
        _COUNT_ZERO,
        [],
    )

    resp = await client.get(f"/ontologies/{oid}/concepts")
    assert resp.status_code == 200

    all_sparql = " ".join(
        str(c.args[0]) for c in ontology_store.sparql_select.call_args_list
    )

    # 필수 TBox 패턴 포함 검증
    assert "a owl:Class" in all_sparql or "rdf:type owl:Class" in all_sparql
    assert "rdfs:subClassOf" in all_sparql


# ── 테스트 3: skos:prefLabel 폴백 ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_concepts_skos_preflabel_in_query(
    client: AsyncClient, ontology_store: AsyncMock, created_ontology: dict
) -> None:
    """list_concepts SPARQL에 skos:prefLabel 폴백 쿼리가 포함되어야 한다."""
    oid = created_ontology["id"]

    ontology_store.sparql_select.side_effect = _make_side_effect(
        _RESOLVE_ROWS,
        _COUNT_ZERO,
        [],
    )

    resp = await client.get(f"/ontologies/{oid}/concepts")
    assert resp.status_code == 200

    all_sparql = " ".join(
        str(c.args[0]) for c in ontology_store.sparql_select.call_args_list
    )

    assert "prefLabel" in all_sparql, (
        "skos:prefLabel 폴백 쿼리가 SPARQL에 없음"
    )


# ── 테스트 4: skos:prefLabel 응답 반환 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_concepts_returns_skos_label(
    client: AsyncClient, ontology_store: AsyncMock, created_ontology: dict
) -> None:
    """skos:prefLabel 만 있는 클래스도 label 필드로 반환되어야 한다."""
    oid = created_ontology["id"]

    ontology_store.sparql_select.side_effect = _make_side_effect(
        _RESOLVE_ROWS,
        [{"total": {"value": "1"}}],
        _CONCEPT_SKOS_ROW,
    )

    resp = await client.get(f"/ontologies/{oid}/concepts")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["label"] == "Plant"
