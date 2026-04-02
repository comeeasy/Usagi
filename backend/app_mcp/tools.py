"""
mcp/tools.py — FastMCP 10종 MCP 도구 정의

MCP 도구 목록 (읽기):
  1. list_ontologies       — 온톨로지 목록 조회
  2. get_ontology_summary  — 온톨로지 요약 + 통계
  3. search_entities       — Entity 검색 (키워드/자연어)
  4. search_relations      — Property 검색
  5. get_subgraph          — 서브그래프 조회
  6. sparql_query          — SPARQL 실행 (SELECT/ASK only)
  7. run_reasoner          — OWL 추론 실행

MCP 도구 목록 (쓰기):
  8. add_individual        — Individual 생성 (owl:NamedIndividual)
  9. update_individual     — Individual 수정 (label/types/properties)
 10. delete_individual     — Individual 삭제

쓰기 도구 사용 패턴 (PDF → Individual):
  1. list_ontologies()으로 대상 온톨로지 IRI 확인
  2. search_entities(kind="concept")으로 매핑할 클래스 IRI 확인
  3. search_relations()으로 사용할 property IRI 확인
  4. add_individual()로 Individual 생성

Named Graph 규칙:
  - 수동 생성 Individual: urn:source:manual/{ontology_id}
  - TBox (스키마):        {ontology_id}/tbox
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


def init_services(store: Any, graph_store: Any, reasoner: Any, vector_index_manager: Any = None) -> None:
    """앱 lifespan에서 호출하여 서비스 인스턴스를 등록."""
    _services["store"] = store
    _services["graph_store"] = graph_store
    _services["reasoner"] = reasoner
    _services["vector_index_manager"] = vector_index_manager
    logger.info("MCP tools: services registered")


# ── 쓰기 도구 공통 헬퍼 ───────────────────────────────────────────────────

_XSD_BASE = "http://www.w3.org/2001/XMLSchema#"
_SPARQL_PREFIXES = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""


def _manual_graph(ontology_id: str) -> str:
    """수동 입력 Individual이 저장되는 Named Graph IRI."""
    return f"urn:source:manual/{ontology_id}"


def _esc(s: str) -> str:
    """SPARQL 문자열 리터럴 내 특수문자 이스케이프."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _xsd_full(xsd: str) -> str:
    """'xsd:string' 형태의 단축 IRI를 전체 IRI로 변환."""
    if xsd.startswith("xsd:"):
        return _XSD_BASE + xsd[4:]
    return xsd if xsd.startswith("http") else _XSD_BASE + xsd


def _parse_list(val: Any) -> list | None:
    """SSE 전송 시 JSON 문자열로 직렬화된 list 파라미터를 파싱."""
    if val is None:
        return None
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        import json
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else None
        except (json.JSONDecodeError, ValueError):
            return None
    return None


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
    use_vector: bool = True,
) -> list[dict]:
    """Entity 검색 MCP 도구 (키워드 + 벡터 하이브리드).

    Args:
        ontology_id: 대상 온톨로지 IRI
        query: 검색 키워드 또는 자연어 문장
        kind: "concept" | "individual" | "all"
        limit: 최대 결과 수
        use_vector: True(기본값)이면 벡터 유사도 검색과 키워드 검색을 함께 수행.
                    벡터 인덱스 미구축 시 키워드 검색으로 자동 폴백.

    Returns:
        [{ iri, label, kind }]
    """
    store = _services.get("store")
    if store is None:
        return []

    # ── 벡터 검색 (use_vector=True) ───────────────────────────────────────
    if use_vector:
        vector_manager = _services.get("vector_index_manager")
        if vector_manager is not None:
            try:
                vec_results = await vector_manager.search(ontology_id, query, limit, store)
                if vec_results:
                    # kind 필터 적용
                    if kind != "all":
                        vec_results = [r for r in vec_results if r.get("kind") == kind]
                    if vec_results:
                        return vec_results[:limit]
            except Exception:
                pass  # 인덱스 미구축 등 → 키워드 검색으로 폴백

    # ── 키워드 검색 (폴백 또는 use_vector=False) ──────────────────────────
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


# ── 쓰기 도구 ─────────────────────────────────────────────────────────────

@mcp.tool()
async def add_individual(
    ontology_id: str,
    iri: str,
    label: str | None = None,
    types: list[str] | None = None,
    data_properties: list[dict] | None = None,
    object_properties: list[dict] | None = None,
    same_as: list[str] | None = None,
    different_from: list[str] | None = None,
) -> dict:
    """Individual(owl:NamedIndividual) 생성 MCP 도구.

    PDF 등 외부 문서에서 추출한 개체를 온톨로지에 등록할 때 사용합니다.
    생성된 Individual은 urn:source:manual/{ontology_id} Named Graph에 저장됩니다.

    Args:
        ontology_id: 대상 온톨로지 IRI (예: "https://infiniq.co.kr/jc3iedm/")
        iri: 생성할 Individual의 IRI (예: "https://infiniq.co.kr/jc3iedm/unit/KST-1")
             중복 IRI는 오류 반환.
        label: rdfs:label 값 (사람이 읽을 수 있는 이름)
        types: rdf:type으로 지정할 클래스 IRI 목록
               search_entities(kind="concept")으로 사용 가능한 클래스를 먼저 확인하세요.
               예: ["https://example.org/ont/MilitaryUnit"]
        data_properties: 데이터 속성 목록. 각 항목은 아래 형태:
               {"property_iri": "...", "value": "...", "datatype": "xsd:string"}
               datatype 기본값은 "xsd:string". 사용 가능한 XSD 타입:
               xsd:string, xsd:integer, xsd:float, xsd:boolean, xsd:dateTime, xsd:date
        object_properties: 객체 속성 목록. 각 항목은 아래 형태:
               {"property_iri": "...", "target_iri": "..."}
               target_iri는 기존에 존재하는 Individual의 IRI여야 합니다.
        same_as: owl:sameAs로 연결할 IRI 목록 (동일 개체를 가리키는 외부 IRI)
        different_from: owl:differentFrom으로 연결할 IRI 목록

    Returns:
        성공: {"status": "created", "iri": "...", "graph_iri": "..."}
        실패: {"error": "오류 메시지"}

    Example:
        add_individual(
            ontology_id="https://infiniq.co.kr/jc3iedm/",
            iri="https://infiniq.co.kr/jc3iedm/unit/KST-1",
            label="1군단",
            types=["https://example.org/ont/MilitaryUnit"],
            data_properties=[
                {"property_iri": "https://example.org/ont/strength", "value": "50000", "datatype": "xsd:integer"}
            ],
        )
    """
    store = _services.get("store")
    graph_store = _services.get("graph_store")
    if store is None:
        return {"error": "store not available"}

    types = _parse_list(types)
    data_properties = _parse_list(data_properties)
    object_properties = _parse_list(object_properties)
    same_as = _parse_list(same_as)
    different_from = _parse_list(different_from)

    # IRI 중복 확인
    exists = await store.sparql_ask(
        f"{_SPARQL_PREFIXES} ASK {{ GRAPH ?g {{ <{iri}> a owl:NamedIndividual }} }}"
    )
    if exists:
        return {"error": f"IRI already exists: {iri}"}

    graph_iri = _manual_graph(ontology_id)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    triples: list[str] = [f"    <{iri}> a owl:NamedIndividual ."]
    if label:
        triples.append(f'    <{iri}> rdfs:label "{_esc(label)}" .')
    for t in (types or []):
        triples.append(f"    <{iri}> rdf:type <{t}> .")
    for dp in (data_properties or []):
        prop = dp.get("property_iri", "")
        val = dp.get("value", "")
        dtype = _xsd_full(dp.get("datatype", "xsd:string"))
        if prop:
            triples.append(f'    <{iri}> <{prop}> "{_esc(str(val))}"^^<{dtype}> .')
    for op in (object_properties or []):
        prop = op.get("property_iri", "")
        target = op.get("target_iri", "")
        if prop and target:
            triples.append(f"    <{iri}> <{prop}> <{target}> .")
    for s in (same_as or []):
        triples.append(f"    <{iri}> owl:sameAs <{s}> .")
    for d in (different_from or []):
        triples.append(f"    <{iri}> owl:differentFrom <{d}> .")
    triples.append(f'    <{iri}> prov:generatedAtTime "{now}"^^xsd:dateTime .')
    triples.append(f'    <{iri}> prov:wasAttributedTo "manual" .')

    await store.sparql_update(
        f"{_SPARQL_PREFIXES}\nINSERT DATA {{ GRAPH <{graph_iri}> {{\n"
        + "\n".join(triples)
        + "\n} }"
    )

    # Neo4j 동기화 (graph_store 미설정 시 RDF 저장은 완료된 상태이므로 경고만 반환)
    if graph_store is not None:
        dp_map = {dp["property_iri"]: dp["value"] for dp in (data_properties or []) if dp.get("property_iri")}
        await graph_store.upsert_individual(ontology_id, iri, label, types or [], dp_map)
        for op in (object_properties or []):
            if op.get("property_iri") and op.get("target_iri"):
                await graph_store.upsert_object_property_value(iri, op["property_iri"], op["target_iri"])
    else:
        logger.warning("add_individual: graph_store not available, Neo4j sync skipped")

    logger.info("add_individual: created %s in %s", iri, graph_iri)
    return {"status": "created", "iri": iri, "graph_iri": graph_iri}


@mcp.tool()
async def update_individual(
    ontology_id: str,
    iri: str,
    label: str | None = None,
    types: list[str] | None = None,
    data_properties: list[dict] | None = None,
    object_properties: list[dict] | None = None,
    same_as: list[str] | None = None,
    different_from: list[str] | None = None,
) -> dict:
    """Individual 수정 MCP 도구.

    지정한 필드만 갱신합니다. None으로 전달한 필드는 변경하지 않습니다.
    리스트 필드(types, data_properties 등)에 빈 리스트([])를 전달하면 해당 필드를 모두 삭제합니다.

    수정 대상은 urn:source:manual/{ontology_id} Named Graph의 트리플입니다.
    Import로 불러온 Individual의 경우 수동 그래프에 변경 트리플이 추가됩니다.

    Args:
        ontology_id: 대상 온톨로지 IRI
        iri: 수정할 Individual의 IRI
        label: 새 rdfs:label. None이면 변경 안 함.
        types: 새 rdf:type 목록. None이면 변경 안 함. []이면 기존 type 모두 삭제.
        data_properties: 새 데이터 속성 목록. None이면 변경 안 함. []이면 모두 삭제.
                각 항목: {"property_iri": "...", "value": "...", "datatype": "xsd:string"}
        object_properties: 새 객체 속성 목록. None이면 변경 안 함. []이면 모두 삭제.
                각 항목: {"property_iri": "...", "target_iri": "..."}
        same_as: 새 owl:sameAs 목록. None이면 변경 안 함.
        different_from: 새 owl:differentFrom 목록. None이면 변경 안 함.

    Returns:
        성공: {"status": "updated", "iri": "..."}
        실패: {"error": "오류 메시지"}
    """
    store = _services.get("store")
    graph_store = _services.get("graph_store")
    if store is None:
        return {"error": "store not available"}

    types = _parse_list(types)
    data_properties = _parse_list(data_properties)
    object_properties = _parse_list(object_properties)
    same_as = _parse_list(same_as)
    different_from = _parse_list(different_from)

    exists = await store.sparql_ask(
        f"{_SPARQL_PREFIXES} ASK {{ GRAPH ?g {{ <{iri}> a owl:NamedIndividual }} }}"
    )
    if not exists:
        return {"error": f"Individual not found: {iri}"}

    g = _manual_graph(ontology_id)

    if label is not None:
        await store.sparql_update(f"""{_SPARQL_PREFIXES}
DELETE {{ GRAPH <{g}> {{ <{iri}> rdfs:label ?o }} }}
INSERT {{ GRAPH <{g}> {{ <{iri}> rdfs:label "{_esc(label)}" }} }}
WHERE  {{ OPTIONAL {{ GRAPH <{g}> {{ <{iri}> rdfs:label ?o }} }} }}""")

    if types is not None:
        await store.sparql_update(f"""{_SPARQL_PREFIXES}
DELETE {{ GRAPH <{g}> {{ <{iri}> rdf:type ?t }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> rdf:type ?t . FILTER(?t != owl:NamedIndividual) }} }}""")
        if types:
            triples = "\n".join([f"    <{iri}> rdf:type <{t}> ." for t in types])
            await store.sparql_update(f"{_SPARQL_PREFIXES}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}")

    if data_properties is not None:
        await store.sparql_update(f"""{_SPARQL_PREFIXES}
DELETE {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> ?p ?o . FILTER(isLiteral(?o))
    FILTER(?p NOT IN (rdfs:label, prov:generatedAtTime, prov:wasAttributedTo)) }} }}""")
        if data_properties:
            triples = "\n".join([
                f'    <{iri}> <{dp["property_iri"]}> "{_esc(str(dp["value"]))}"^^<{_xsd_full(dp.get("datatype", "xsd:string"))}> .'
                for dp in data_properties if dp.get("property_iri")
            ])
            if triples:
                await store.sparql_update(f"{_SPARQL_PREFIXES}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}")

    if object_properties is not None:
        await store.sparql_update(f"""{_SPARQL_PREFIXES}
DELETE {{ GRAPH <{g}> {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> ?p ?o . FILTER(isIRI(?o))
    FILTER(?p NOT IN (rdf:type, owl:sameAs, owl:differentFrom)) }} }}""")
        if object_properties:
            triples = "\n".join([
                f"    <{iri}> <{op['property_iri']}> <{op['target_iri']}> ."
                for op in object_properties if op.get("property_iri") and op.get("target_iri")
            ])
            if triples:
                await store.sparql_update(f"{_SPARQL_PREFIXES}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}")

    for pred_str, vals in [("owl:sameAs", same_as), ("owl:differentFrom", different_from)]:
        if vals is not None:
            await store.sparql_update(f"""{_SPARQL_PREFIXES}
DELETE {{ GRAPH <{g}> {{ <{iri}> {pred_str} ?o }} }}
WHERE  {{ GRAPH <{g}> {{ <{iri}> {pred_str} ?o }} }}""")
            if vals:
                triples = "\n".join([f"    <{iri}> {pred_str} <{v}> ." for v in vals])
                await store.sparql_update(f"{_SPARQL_PREFIXES}\nINSERT DATA {{ GRAPH <{g}> {{\n{triples}\n}} }}")

    # Neo4j 동기화
    if graph_store is not None:
        dp_map = {dp["property_iri"]: dp["value"] for dp in (data_properties or []) if dp.get("property_iri")}
        await graph_store.upsert_individual(ontology_id, iri, label or "", types or [], dp_map)
        if object_properties is not None:
            await graph_store.sync_object_property_values(
                iri,
                [{"property_iri": op["property_iri"], "target_iri": op["target_iri"]}
                 for op in object_properties if op.get("property_iri") and op.get("target_iri")],
            )
    else:
        logger.warning("update_individual: graph_store not available, Neo4j sync skipped")

    logger.info("update_individual: updated %s", iri)
    return {"status": "updated", "iri": iri}


@mcp.tool()
async def add_concept(
    ontology_id: str,
    iri: str,
    label: str,
    super_classes: list[str] | None = None,
    description: str | None = None,
) -> dict:
    """Concept(owl:Class) 생성 MCP 도구.

    온톨로지의 TBox에 새 클래스를 추가합니다.
    기존 클래스를 확장하거나, 문서에서 추출한 새 도메인 개념을 등록할 때 사용합니다.

    Args:
        ontology_id: 대상 온톨로지 IRI (예: "https://infiniq.co.kr/jc3iedm/")
        iri: 생성할 Concept의 IRI (예: "https://infiniq.co.kr/jc3iedm/SpecialForces")
             중복 IRI는 오류 반환.
        label: rdfs:label 값 (사람이 읽을 수 있는 이름)
        super_classes: rdfs:subClassOf로 연결할 부모 클래스 IRI 목록
                       search_entities(kind="concept")으로 후보를 먼저 확인하세요.
                       예: ["https://infiniq.co.kr/jc3iedm/MilitaryOrganisation"]
        description: rdfs:comment 값 (선택)

    Returns:
        성공: {"status": "created", "iri": "...", "graph_iri": "..."}
        실패: {"error": "오류 메시지"}

    Example:
        add_concept(
            ontology_id="https://infiniq.co.kr/jc3iedm/",
            iri="https://infiniq.co.kr/jc3iedm/SpecialForces",
            label="특수부대",
            super_classes=["https://infiniq.co.kr/jc3iedm/MilitaryOrganisation"],
        )
    """
    store = _services.get("store")
    graph_store = _services.get("graph_store")
    if store is None:
        return {"error": "store not available"}

    super_classes = _parse_list(super_classes)

    # IRI 중복 확인
    exists = await store.sparql_ask(
        f"{_SPARQL_PREFIXES} ASK {{ GRAPH ?g {{ <{iri}> a owl:Class }} }}"
    )
    if exists:
        return {"error": f"IRI already exists: {iri}"}

    # TBox 그래프에 추가
    tbox_graph = f"{ontology_id}/tbox"
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    triples: list[str] = [
        f"    <{iri}> a owl:Class .",
        f'    <{iri}> rdfs:label "{_esc(label)}" .',
    ]
    for sc in (super_classes or []):
        triples.append(f"    <{iri}> rdfs:subClassOf <{sc}> .")
    if description:
        triples.append(f'    <{iri}> rdfs:comment "{_esc(description)}" .')
    triples.append(f'    <{iri}> prov:generatedAtTime "{now}"^^xsd:dateTime .')
    triples.append(f'    <{iri}> prov:wasAttributedTo "manual" .')

    await store.sparql_update(
        f"{_SPARQL_PREFIXES}\nINSERT DATA {{ GRAPH <{tbox_graph}> {{\n"
        + "\n".join(triples)
        + "\n} }"
    )

    # Neo4j 동기화
    if graph_store is not None:
        await graph_store.upsert_concept(ontology_id, iri, label, super_classes or [])
    else:
        logger.warning("add_concept: graph_store not available, Neo4j sync skipped")

    logger.info("add_concept: created %s in %s", iri, tbox_graph)
    return {"status": "created", "iri": iri, "graph_iri": tbox_graph}


@mcp.tool()
async def delete_individual(ontology_id: str, iri: str) -> dict:
    """Individual 삭제 MCP 도구.

    모든 Named Graph에서 해당 IRI를 주어(subject)로 갖는 트리플을 전부 삭제합니다.
    삭제 후 복구가 불가능하므로 신중하게 사용하세요.

    Args:
        ontology_id: 대상 온톨로지 IRI (Neo4j 동기화에 사용)
        iri: 삭제할 Individual의 IRI

    Returns:
        성공: {"status": "deleted", "iri": "..."}
        실패: {"error": "오류 메시지"}
    """
    store = _services.get("store")
    graph_store = _services.get("graph_store")
    if store is None:
        return {"error": "store not available"}

    exists = await store.sparql_ask(
        f"{_SPARQL_PREFIXES} ASK {{ GRAPH ?g {{ <{iri}> a owl:NamedIndividual }} }}"
    )
    if not exists:
        return {"error": f"Individual not found: {iri}"}

    # 모든 Named Graph에서 해당 Individual의 트리플 삭제
    await store.sparql_update(f"""{_SPARQL_PREFIXES}
DELETE {{ GRAPH ?g {{ <{iri}> ?p ?o }} }}
WHERE  {{ GRAPH ?g {{ <{iri}> ?p ?o }} }}""")
    # Default graph 트리플도 삭제
    await store.sparql_update(f"{_SPARQL_PREFIXES}\nDELETE WHERE {{ <{iri}> ?p ?o }}")

    if graph_store is not None:
        await graph_store.delete_node(iri)
    else:
        logger.warning("delete_individual: graph_store not available, Neo4j sync skipped")

    logger.info("delete_individual: deleted %s", iri)
    return {"status": "deleted", "iri": iri}
