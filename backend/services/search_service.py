"""
Search Service — 검색 (SPARQL 키워드 검색 + 벡터 검색 폴백)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ontology_store import OntologyStore


def _v(term: dict | None, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


async def search_entities(
    ontology_id: str,
    q: str,
    kind: str | None = None,
    limit: int = 20,
    store: "OntologyStore | None" = None,
) -> list:
    """
    SPARQL FILTER(CONTAINS(LCASE(STR(?label)), ...)) 로 키워드 검색.
    kind='concept'이면 owl:Class만, 'individual'이면 owl:NamedIndividual만.
    store가 None이면 빈 리스트 반환.
    """
    if store is None:
        return []

    tbox = f"{ontology_id}/tbox"
    q_filter = f'FILTER(CONTAINS(LCASE(STR(?label)), "{_esc(q.lower())}"))' if q else ""
    results = []

    if kind in ("concept", "all", None):
        rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label WHERE {{
    GRAPH <{tbox}> {{
        ?iri a owl:Class .
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {q_filter}
    }}
}} ORDER BY ?label LIMIT {limit}""")
        for r in rows:
            results.append({
                "iri": _v(r.get("iri")),
                "label": _v(r.get("label")) or _v(r.get("iri")),
                "kind": "concept",
            })

    if kind in ("individual", "all", None):
        remaining = limit - len(results)
        if remaining > 0:
            rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label WHERE {{
    GRAPH <{tbox}> {{
        ?iri a owl:NamedIndividual .
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {q_filter}
    }}
}} ORDER BY ?label LIMIT {remaining}""")
            for r in rows:
                results.append({
                    "iri": _v(r.get("iri")),
                    "label": _v(r.get("label")) or _v(r.get("iri")),
                    "kind": "individual",
                })

    return results[:limit]


async def search_relations(
    ontology_id: str,
    q: str,
    domain_iri: str | None = None,
    range_iri: str | None = None,
    limit: int = 20,
    store: "OntologyStore | None" = None,
) -> list:
    """
    ObjectProperty + DataProperty SPARQL 검색, domain/range 필터 옵션.
    store가 None이면 빈 리스트 반환.
    """
    if store is None:
        return []

    tbox = f"{ontology_id}/tbox"
    q_filter = f'FILTER(CONTAINS(LCASE(STR(?label)), "{_esc(q.lower())}"))' if q else ""
    domain_filter = f"?iri rdfs:domain <{domain_iri}> ." if domain_iri else ""
    range_filter = f"?iri rdfs:range <{range_iri}> ." if range_iri else ""

    rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label ?kind WHERE {{
    GRAPH <{tbox}> {{
        {{ ?iri a owl:ObjectProperty . BIND("object" AS ?kind) }}
        UNION
        {{ ?iri a owl:DatatypeProperty . BIND("data" AS ?kind) }}
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {q_filter}
        {domain_filter}
        {range_filter}
    }}
}} ORDER BY ?label LIMIT {limit}""")

    results = []
    for r in rows:
        results.append({
            "iri": _v(r.get("iri")),
            "label": _v(r.get("label")) or _v(r.get("iri")),
            "kind": _v(r.get("kind")),
        })
    return results


async def vector_search(
    ontology_id: str,
    text: str,
    k: int = 10,
    store: "OntologyStore | None" = None,
) -> list:
    """
    임베딩 기반 유사 Entity 검색.
    벡터 DB 미구축 시 search_entities로 폴백.
    """
    return await search_entities(ontology_id, text, limit=k, store=store)
