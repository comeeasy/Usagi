"""
api/search.py — Entity/Relation 검색 라우터

엔드포인트:
  GET  /ontologies/{id}/search/entities    키워드 Entity 검색
  GET  /ontologies/{id}/search/relations   키워드 Property 검색
  POST /ontologies/{id}/search/vector      임베딩 벡터 검색 (폴백: 키워드 검색)
"""

from collections import defaultdict
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from services.ontology_graph import resolve_kg_graph_iri
from services.ontology_scope import ontology_iri_from_tbox

router = APIRouter(prefix="/ontologies/{ontology_id}/search", tags=["search"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
"""


def _v(term: dict | None, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


async def _resolve_kg_graph(store, ontology_id: str, dataset: str | None = None) -> str | None:
    """UUID(dc:identifier)로 kg Named Graph IRI 반환. 없으면 None."""
    return await resolve_kg_graph_iri(store, ontology_id, dataset=dataset)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


class VectorSearchRequest(BaseModel):
    text: str
    k: int = 10


# ── Entity 검색 ───────────────────────────────────────────────────────────

@router.get("/entities")
async def search_entities(
    request: Request,
    ontology_id: str,
    q: str = Query("", description="키워드"),
    kind: Literal["concept", "individual", "all"] = Query("all"),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str | None = Query(None),
) -> list[dict]:
    """
    rdfs:label 기반 키워드 검색.
    kind: concept(owl:Class) / individual(owl:NamedIndividual) / all
    """
    store = request.app.state.ontology_store
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        return []

    ql = _esc(q.lower()) if q else ""
    q_filter = ""
    if q and ql:
        q_filter = f"""FILTER(
      CONTAINS(LCASE(STR(?iri)), "{ql}") ||
      (bound(?label) && CONTAINS(LCASE(STR(?label)), "{ql}"))
    )"""

    _class_pat = """
        { ?iri a owl:Class }
        UNION
        { ?iri a rdfs:Class . FILTER NOT EXISTS { ?iri a owl:Ontology } }
        UNION
        { ?iri a skos:Concept }
    """

    results = []

    # Concept 검색
    if kind in ("concept", "all"):
        rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label WHERE {{
    GRAPH <{kg}> {{
        {_class_pat}
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {q_filter}
    }}
}} ORDER BY ?label LIMIT {limit}""", dataset=dataset)
        for r in rows:
            results.append({
                "iri": _v(r.get("iri")),
                "label": _v(r.get("label")) or _v(r.get("iri")),
                "kind": "concept",
            })

    _ind_pat = f"""
        {{
          ?iri a owl:NamedIndividual
        }} UNION {{
          ?iri rdf:type ?ctype .
          {{
            GRAPH <{kg}> {{ ?ctype a owl:Class }}
          }} UNION {{
            GRAPH <{kg}> {{ ?ctype a rdfs:Class .
            FILTER NOT EXISTS {{ ?ctype a owl:Ontology }} }}
          }}
          FILTER NOT EXISTS {{ GRAPH <{kg}> {{ ?iri a owl:Class }} }}
          FILTER NOT EXISTS {{ GRAPH <{kg}> {{ ?iri a rdfs:Class }} }}
        }}
    """

    # Individual 검색 (kg 단일 그래프)
    if kind in ("individual", "all"):
        remaining = limit - len(results)
        if remaining > 0:
            rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label WHERE {{
    GRAPH <{kg}> {{
        {_ind_pat}
        OPTIONAL {{ ?iri rdfs:label ?label }}
        {q_filter}
    }}
}} ORDER BY ?label LIMIT {remaining}""", dataset=dataset)
            types_by_iri: dict[str, list[str]] = defaultdict(list)
            if rows:
                iris_vals = " ".join(f"<{_v(r.get('iri'))}>" for r in rows)
                type_rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?t WHERE {{
    VALUES ?iri {{ {iris_vals} }}
    GRAPH <{kg}> {{
        ?iri rdf:type ?t .
        FILTER(?t != owl:NamedIndividual) FILTER(isIRI(?t))
    }}
}}""", dataset=dataset)
                for tr in type_rows:
                    types_by_iri[_v(tr.get("iri"))].append(_v(tr.get("t")))
            for r in rows:
                iri_v = _v(r.get("iri"))
                results.append({
                    "iri": iri_v,
                    "label": _v(r.get("label")) or iri_v,
                    "kind": "individual",
                    "types": types_by_iri.get(iri_v, []),
                })

    return results


# ── Relation 검색 ─────────────────────────────────────────────────────────

@router.get("/relations")
async def search_relations(
    request: Request,
    ontology_id: str,
    q: str = Query("", description="키워드"),
    domain_iri: str | None = Query(None, alias="domain"),
    range_iri: str | None = Query(None, alias="range"),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str | None = Query(None),
) -> list[dict]:
    """ObjectProperty + DataProperty 키워드 검색."""
    store = request.app.state.ontology_store
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        return []

    q_filter = f'FILTER(CONTAINS(LCASE(STR(?label)), "{_esc(q.lower())}"))' if q else ""
    domain_filter = f"?iri rdfs:domain <{domain_iri}> ." if domain_iri else ""
    range_filter = f"?iri rdfs:range <{range_iri}> ." if range_iri else ""

    rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?label ?kind
       (GROUP_CONCAT(DISTINCT STR(?domain); SEPARATOR="\t") AS ?domains)
       (GROUP_CONCAT(DISTINCT STR(?range);  SEPARATOR="\t") AS ?ranges)
WHERE {{
    GRAPH <{kg}> {{
        {{ ?iri a owl:ObjectProperty . BIND("object" AS ?kind) }}
        UNION
        {{ ?iri a owl:DatatypeProperty . BIND("data" AS ?kind) }}
        OPTIONAL {{ ?iri rdfs:label  ?label  }}
        OPTIONAL {{ ?iri rdfs:domain ?domain . FILTER(isIRI(?domain)) }}
        OPTIONAL {{ ?iri rdfs:range  ?range  }}
        {q_filter}
        {domain_filter}
        {range_filter}
    }}
}} GROUP BY ?iri ?label ?kind
ORDER BY ?label LIMIT {limit}""", dataset=dataset)

    results = []
    for r in rows:
        iri = _v(r.get("iri"))
        domains_raw = _v(r.get("domains"))
        ranges_raw = _v(r.get("ranges"))
        results.append({
            "iri": iri,
            "label": _v(r.get("label")) or iri,
            "kind": _v(r.get("kind")),
            "domain": [d for d in domains_raw.split("\t") if d] if domains_raw else [],
            "range":  [r_ for r_ in ranges_raw.split("\t") if r_] if ranges_raw else [],
        })

    return results


# ── 벡터 검색 ─────────────────────────────────────────────────────────────

@router.post("/vector")
async def vector_search(
    request: Request,
    ontology_id: str,
    body: VectorSearchRequest,
    dataset: str | None = Query(None),
) -> list[dict]:
    """
    fastembed 기반 코사인 유사도 검색.
    인덱스 미구축 또는 빈 온톨로지 시 키워드 검색으로 폴백.
    """
    store = request.app.state.ontology_store
    manager = getattr(request.app.state, "vector_index_manager", None)

    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        return []

    ontology_iri = ontology_iri_from_tbox(kg)

    if manager is not None:
        try:
            results = await manager.search(ontology_iri, body.text, body.k, store)
            if results:
                return results
        except Exception:
            pass  # 임베딩 모델 로드 실패 등 → 폴백

    # 폴백: 키워드 검색
    return await search_entities(request, ontology_id, q=body.text, kind="all", limit=body.k, dataset=dataset)
