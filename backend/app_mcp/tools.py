"""
mcp/tools.py — FastMCP 7종 MCP 도구 정의

MCP 도구 목록:
  1. list_ontologies       — 온톨로지 목록 조회
  2. get_ontology_summary  — 온톨로지 요약 + 통계
  3. search_entities       — Entity 검색 (키워드/자연어)
  4. search_relations      — Property 검색
  5. get_subgraph          — 서브그래프 조회
  6. sparql_query          — SPARQL 실행 (SELECT/ASK only)
  7. run_reasoner          — OWL 추론 실행
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("Ontology Platform")

# Module-level service holders; populated during app startup via init_services()
_services: dict[str, Any] = {}


def init_services(store: Any, graph_store: Any, reasoner: Any) -> None:
    """앱 lifespan에서 호출하여 서비스 인스턴스를 등록."""
    _services["store"] = store
    _services["graph_store"] = graph_store
    _services["reasoner"] = reasoner
    logger.info("MCP tools: services registered")


@mcp.tool()
async def list_ontologies() -> list[dict]:
    """온톨로지 목록 조회 MCP 도구.

    Returns:
        온톨로지 목록 (iri, label, version 포함)
    """
    store = _services.get("store")
    if store is None:
        return []
    items, _total = await store.list_ontologies(1, 50)
    return items


@mcp.tool()
async def get_ontology_summary(ontology_id: str) -> dict:
    """온톨로지 요약 및 통계 조회.

    Args:
        ontology_id: 온톨로지 IRI

    Returns:
        통계 딕셔너리 (concepts, individuals, object_properties, data_properties, named_graphs)
    """
    store = _services.get("store")
    if store is None:
        return {"error": "store not available"}
    tbox_iri = f"{ontology_id}/tbox"
    stats = await store.get_ontology_stats(tbox_iri)
    return {"ontology_id": ontology_id, "stats": stats}


@mcp.tool()
async def search_entities(
    ontology_id: str,
    query: str,
    kind: str = "all",
    limit: int = 10,
) -> list[dict]:
    """Entity 검색 MCP 도구 (키워드).

    Args:
        ontology_id: 대상 온톨로지 IRI
        query: 검색 키워드
        kind: "concept" | "individual" | "all"
        limit: 최대 결과 수

    Returns:
        [{ iri, label, kind }]
    """
    store = _services.get("store")
    if store is None:
        return []

    tbox_iri = f"{ontology_id}/tbox"
    results: list[dict] = []

    if kind in ("concept", "all"):
        sparql = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?iri ?label WHERE {{
                GRAPH <{tbox_iri}> {{
                    ?iri a owl:Class .
                    OPTIONAL {{ ?iri rdfs:label ?label }}
                }}
                FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("{query}"))
                       || CONTAINS(LCASE(STR(?label)), LCASE("{query}")))
            }}
            LIMIT {limit}
        """
        rows = await store.sparql_select(sparql)
        for row in rows:
            iri = row.get("iri", {}).get("value", "")
            label = row.get("label", {}).get("value", iri)
            if iri:
                results.append({"iri": iri, "label": label, "kind": "concept"})

    if kind in ("individual", "all"):
        remaining = limit - len(results)
        if remaining > 0:
            sparql = f"""
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?iri ?label WHERE {{
                    GRAPH <{tbox_iri}> {{
                        ?iri a owl:NamedIndividual .
                        OPTIONAL {{ ?iri rdfs:label ?label }}
                    }}
                    FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("{query}"))
                           || CONTAINS(LCASE(STR(?label)), LCASE("{query}")))
                }}
                LIMIT {remaining}
            """
            rows = await store.sparql_select(sparql)
            for row in rows:
                iri = row.get("iri", {}).get("value", "")
                label = row.get("label", {}).get("value", iri)
                if iri:
                    results.append({"iri": iri, "label": label, "kind": "individual"})

    return results[:limit]


@mcp.tool()
async def search_relations(
    ontology_id: str,
    query: str = "",
    limit: int = 10,
) -> list[dict]:
    """Property(Relation) 검색 MCP 도구.

    Args:
        ontology_id: 대상 온톨로지 IRI
        query: 검색 키워드 (빈 문자열이면 전체 조회)
        limit: 최대 결과 수

    Returns:
        [{ iri, label, kind }]
    """
    store = _services.get("store")
    if store is None:
        return []

    tbox_iri = f"{ontology_id}/tbox"
    filter_clause = ""
    if query:
        filter_clause = (
            f'FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("{query}")) '
            f'|| CONTAINS(LCASE(STR(?label)), LCASE("{query}")))'
        )

    sparql = f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?iri ?label ?kind WHERE {{
            GRAPH <{tbox_iri}> {{
                {{ ?iri a owl:ObjectProperty . BIND("object" AS ?kind) }}
                UNION
                {{ ?iri a owl:DatatypeProperty . BIND("data" AS ?kind) }}
                OPTIONAL {{ ?iri rdfs:label ?label }}
            }}
            {filter_clause}
        }}
        LIMIT {limit}
    """

    rows = await store.sparql_select(sparql)
    results = []
    for row in rows:
        iri = row.get("iri", {}).get("value", "")
        label = row.get("label", {}).get("value", iri)
        kind = row.get("kind", {}).get("value", "unknown")
        if iri:
            results.append({"iri": iri, "label": label, "kind": kind})
    return results


@mcp.tool()
async def get_subgraph(
    ontology_id: str,
    entity_iris: list[str],
    depth: int = 2,
) -> dict:
    """서브그래프 조회 MCP 도구.

    Args:
        ontology_id: 대상 온톨로지 IRI
        entity_iris: 시작 엔티티 IRI 목록
        depth: 탐색 깊이 (1-5, 기본 2)

    Returns:
        { nodes: [...], edges: [...] }
    """
    graph_store = _services.get("graph_store")
    if graph_store is None:
        return {"nodes": [], "edges": [], "error": "graph_store not available"}
    depth = max(1, min(depth, 5))
    return await graph_store.get_subgraph(ontology_id, entity_iris, depth)


@mcp.tool()
async def sparql_query(ontology_id: str, query: str) -> dict:
    """SPARQL 쿼리 실행 MCP 도구 (SELECT / ASK만 허용).

    Args:
        ontology_id: 대상 온톨로지 IRI (컨텍스트용)
        query: SPARQL SELECT 또는 ASK 쿼리

    Returns:
        { results: [...] } 또는 오류 딕셔너리
    """
    store = _services.get("store")
    if store is None:
        return {"error": "store not available"}

    # Block mutating queries
    upper = query.upper()
    for forbidden in ("UPDATE", "INSERT", "DELETE", "DROP", "CREATE", "LOAD", "CLEAR"):
        if forbidden in upper:
            return {"error": f"Mutating SPARQL operation '{forbidden}' is not allowed"}

    rows = await store.sparql_select(query)
    return {"results": rows}


@mcp.tool()
async def run_reasoner(
    ontology_id: str,
    entity_iris: list[str] | None = None,
) -> dict:
    """OWL 2 추론 실행 MCP 도구.

    Args:
        ontology_id: 대상 온톨로지 IRI
        entity_iris: 범위를 제한할 엔티티 IRI 목록 (None이면 전체)

    Returns:
        { consistent, violations, inferred_axioms_count, job_id } 또는 오류 딕셔너리
    """
    reasoner = _services.get("reasoner")
    if reasoner is None:
        return {"error": "reasoner not available"}

    # Start reasoner job and poll until completion (max 120s)
    job_id = await reasoner.run(ontology_id, entity_iris)

    timeout = 120.0
    poll_interval = 1.0
    elapsed = 0.0

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        job = await reasoner.get_result(job_id)
        status = job.get("status")

        if status == "completed":
            result = job.get("result")
            if result is None:
                return {"job_id": job_id, "status": "completed", "error": "no result"}
            return {
                "job_id": job_id,
                "consistent": result.consistent,
                "violations": [v.model_dump() for v in result.violations],
                "inferred_axioms_count": len(result.inferred_axioms),
                "execution_ms": result.execution_ms,
            }

        if status == "failed":
            return {"job_id": job_id, "status": "failed", "error": job.get("error")}

    return {"job_id": job_id, "status": "timeout", "error": "Reasoner timed out after 120s"}
