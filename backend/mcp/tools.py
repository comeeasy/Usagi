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

# from fastmcp import FastMCP
# from mcp import mcp  # 공유 인스턴스
# from services.ontology_store import OntologyStore
# from services.graph_store import GraphStore
# from services.search_service import SearchService
# from services.reasoner_service import ReasonerService


# @mcp.tool()
async def list_ontologies() -> list[dict]:
    """
    온톨로지 목록 조회 MCP 도구.

    구현 세부사항:
    - OntologyStore.list_ontologies(page=1, page_size=100) 호출
    - 반환: [{ id, iri, label, stats: { concepts, individuals, objectProperties, dataProperties } }]
    - AI 에이전트가 작업할 온톨로지를 선택하는 첫 단계로 사용
    """
    pass


# @mcp.tool()
async def get_ontology_summary(ontology_id: str) -> dict:
    """
    온톨로지 요약 및 통계 조회.

    구현 세부사항:
    - OntologyStore.get_ontology_stats(ontology_id) 호출
    - 반환: { iri, label, description, stats: { concepts, individuals, objectProperties, dataProperties } }
    - AI 에이전트가 온톨로지 구조를 파악하는 용도
    """
    pass


# @mcp.tool()
async def search_entities(
    ontology_id: str,
    query: str,
    kind: str = "all",
    limit: int = 10,
) -> list[dict]:
    """
    Entity 검색 MCP 도구 (키워드 또는 자연어).

    구현 세부사항:
    - SearchService.keyword_search_entities(ontology_id, query, kind, limit) 호출
    - query: 키워드 또는 자연어 (현재는 키워드 검색, 향후 NL2SPARQL 확장 가능)
    - kind: "concept" | "individual" | "all"
    - 반환: [{ iri, label, kind, types?, matchScore }]
    - AI 에이전트가 특정 엔티티를 찾을 때 사용
    """
    pass


# @mcp.tool()
async def search_relations(
    ontology_id: str,
    query: str | None = None,
    domain_iri: str | None = None,
    range_iri: str | None = None,
    kind: str = "all",
    limit: int = 10,
) -> list[dict]:
    """
    Property(Relation) 검색 MCP 도구.

    구현 세부사항:
    - SearchService.keyword_search_relations() 호출
    - 반환: [{ iri, label, kind, domain, range, characteristics }]
    - AI 에이전트가 도메인/레인지로 관계를 탐색할 때 사용
    """
    pass


# @mcp.tool()
async def get_subgraph(
    ontology_id: str,
    entity_iris: list[str],
    depth: int = 2,
) -> dict:
    """
    서브그래프 조회 MCP 도구.

    구현 세부사항:
    - GraphStore.get_subgraph(ontology_id, entity_iris, depth) 호출
    - depth: 1-5 (기본값 2)
    - 반환: {
        nodes: [{ iri, label, kind, types }],
        edges: [{ source, target, propertyIri, propertyLabel, kind }]
      }
    - AI 에이전트가 엔티티 주변 관계를 탐색할 때 사용
    """
    pass


# @mcp.tool()
async def sparql_query(ontology_id: str, query: str) -> dict:
    """
    SPARQL 쿼리 실행 MCP 도구 (SELECT / ASK만 허용).

    구현 세부사항:
    - UPDATE/INSERT/DELETE 키워드 감지 시 오류 반환 (보안)
    - OntologyStore.sparql_select(ontology_id, query) 호출
    - 반환: {
        variables: [str, ...],
        bindings: [{ var: { type, value, datatype? } }, ...]
      }
    - AI 에이전트가 복잡한 온톨로지 질의를 수행할 때 사용
    """
    pass


# @mcp.tool()
async def run_reasoner(
    ontology_id: str,
    entity_iris: list[str] | None = None,
) -> dict:
    """
    OWL 2 추론 실행 MCP 도구.

    구현 세부사항:
    - ReasonerService.run(ontology_id, entity_iris) 동기적으로 await
      (MCP 도구는 결과를 직접 반환해야 하므로 Job 폴링 없이 완료까지 대기)
    - 반환: {
        consistent: bool,
        violations: [{ type, subjectIri, description }],
        inferredAxiomsCount: int
      }
    - AI 에이전트가 온톨로지 정합성을 검증할 때 사용
    - 타임아웃: 120초 (대형 온톨로지의 경우 entity_iris로 범위 제한 권장)
    """
    pass
