"""
api/search.py — Entity/Relation 검색 라우터

엔드포인트:
  GET  /ontologies/{id}/search/entities    키워드 Entity 검색
  GET  /ontologies/{id}/search/relations   키워드 Property 검색
  POST /ontologies/{id}/search/vector      임베딩 벡터 검색 (폴백: 키워드 검색)
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/ontologies/{ontology_id}/search", tags=["search"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


def _v(term: dict | None, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


async def _resolve_tbox(store, ontology_id: str) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 조회 후 tbox IRI 반환. 없으면 None."""
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX dc:  <http://purl.org/dc/terms/>
        SELECT ?iri WHERE {{
            GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{ontology_id}" }}
        }} LIMIT 1
    """)
    if not rows:
        return None
    return f"{rows[0]['iri']['value']}/tbox"


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
) -> list[dict]:
    """
    rdfs:label 기반 키워드 검색.
    kind: concept(owl:Class) / individual(owl:NamedIndividual) / all
    """
    store = request.app.state.ontology_store
    tbox = await _resolve_tbox(store, ontology_id)
    if tbox is None:
        return []

    q_filter = f'FILTER(CONTAINS(LCASE(STR(?label)), "{_esc(q.lower())}"))' if q else ""

    results = []

    # Concept 검색
    if kind in ("concept", "all"):
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

    # Individual 검색
    if kind in ("individual", "all"):
        remaining = limit - len(results)
        if remaining > 0:
            rows = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri ?label WHERE {{
    GRAPH ?g {{
        ?iri a owl:NamedIndividual .
        OPTIONAL {{ ?iri rdfs:label ?label }}
    }}
    {q_filter}
}} ORDER BY ?label LIMIT {remaining}""")
            for r in rows:
                type_rows = await store.sparql_select(f"""{_P}
SELECT ?t WHERE {{ GRAPH ?g {{ <{_v(r.get("iri"))}> rdf:type ?t . FILTER(?t != owl:NamedIndividual) FILTER(isIRI(?t)) }} }}""")
                results.append({
                    "iri": _v(r.get("iri")),
                    "label": _v(r.get("label")) or _v(r.get("iri")),
                    "kind": "individual",
                    "types": [_v(tr.get("t")) for tr in type_rows],
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
) -> list[dict]:
    """ObjectProperty + DataProperty 키워드 검색."""
    store = request.app.state.ontology_store
    tbox = await _resolve_tbox(store, ontology_id)
    if tbox is None:
        return []

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
        iri = _v(r.get("iri"))
        domain_rows = await store.sparql_select(
            f"{_P}\nSELECT ?d WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:domain ?d . FILTER(isIRI(?d)) }} }}")
        range_rows = await store.sparql_select(
            f"{_P}\nSELECT ?r WHERE {{ GRAPH <{tbox}> {{ <{iri}> rdfs:range ?r }} }}")
        results.append({
            "iri": iri,
            "label": _v(r.get("label")) or iri,
            "kind": _v(r.get("kind")),
            "domain": [_v(dr.get("d")) for dr in domain_rows],
            "range": [_v(rr.get("r")) for rr in range_rows],
        })

    return results


# ── 벡터 검색 ─────────────────────────────────────────────────────────────

@router.post("/vector")
async def vector_search(request: Request, ontology_id: str, body: VectorSearchRequest) -> list[dict]:
    """
    fastembed 기반 코사인 유사도 검색.
    인덱스 미구축 또는 빈 온톨로지 시 키워드 검색으로 폴백.
    """
    store = request.app.state.ontology_store
    manager = getattr(request.app.state, "vector_index_manager", None)

    tbox = await _resolve_tbox(store, ontology_id)
    if tbox is None:
        return []

    ontology_iri = tbox[: -len("/tbox")]

    if manager is not None:
        try:
            results = await manager.search(ontology_iri, body.text, body.k, store)
            if results:
                return results
        except Exception:
            pass  # 임베딩 모델 로드 실패 등 → 폴백

    # 폴백: 키워드 검색
    return await search_entities(request, ontology_id, q=body.text, kind="all", limit=body.k)
