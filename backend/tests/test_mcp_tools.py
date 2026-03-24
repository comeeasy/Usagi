"""
Tests for MCP tools (app_mcp/tools.py).

MCP 도구는 _services 딕셔너리를 통해 서비스를 주입받는다.
각 테스트에서 init_services()로 인메모리 Store + Mock 서비스를 주입.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app_mcp.tools import (
    init_services,
    list_ontologies,
    get_ontology_summary,
    search_entities,
    search_relations,
    get_subgraph,
    sparql_query,
    run_reasoner,
)
from services.ontology_store import OntologyStore
from services.reasoner_service import ReasonerService


ONT_IRI = "https://test.example.org/onto"
TBOX = f"{ONT_IRI}/tbox"

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


@pytest.fixture
async def store():
    return OntologyStore(path=None)


@pytest.fixture
def mock_graph_store():
    mock = AsyncMock()
    mock.get_subgraph.return_value = {
        "nodes": [{"id": f"{ONT_IRI}#Person", "label": "Person", "kind": "concept"}],
        "edges": [],
    }
    return mock


@pytest.fixture
def mock_reasoner():
    mock = AsyncMock()
    mock.run.return_value = "test-job-id"
    result = MagicMock()
    result.consistent = True
    result.violations = []
    result.inferred_axioms = []
    result.execution_ms = 10
    mock.get_result.return_value = {"status": "completed", "result": result}
    return mock


@pytest.fixture(autouse=True)
async def setup_services(store, mock_graph_store, mock_reasoner):
    """각 테스트마다 서비스 재주입 (모듈 레벨 _services 초기화)."""
    init_services(store, mock_graph_store, mock_reasoner)
    yield
    init_services(None, None, None)  # 정리


@pytest.fixture
async def populated_store(store):
    """Concept / Individual / Property가 있는 Store."""
    await store.sparql_update(f"""{_P}
        INSERT DATA {{
            GRAPH <{TBOX}> {{
                <{ONT_IRI}#Person> a owl:Class ; rdfs:label "Person" .
                <{ONT_IRI}#Employee> a owl:Class ; rdfs:label "Employee" .
                <{ONT_IRI}#alice> a owl:NamedIndividual ; rdfs:label "Alice" .
                <{ONT_IRI}#hasJob> a owl:ObjectProperty ; rdfs:label "hasJob" .
                <{ONT_IRI}#age> a owl:DatatypeProperty ; rdfs:label "age" .
            }}
        }}
    """)
    return store


# ── list_ontologies ────────────────────────────────────────────────────────────

async def test_mcp_list_ontologies_empty(store):
    """Store가 비어있으면 빈 리스트 반환."""
    result = await list_ontologies()
    assert isinstance(result, list)
    assert result == []


async def test_mcp_list_ontologies_returns_items(store):
    """온톨로지 존재 시 목록 반환."""
    await store.sparql_update(f"""{_P}
        PREFIX dc: <http://purl.org/dc/terms/>
        INSERT DATA {{
            GRAPH <{TBOX}> {{
                <{ONT_IRI}> a owl:Ontology ; rdfs:label "Test Onto" ; dc:identifier "abc-123" .
            }}
        }}
    """)
    result = await list_ontologies()
    assert isinstance(result, list)
    assert len(result) >= 1
    assert any(r.get("iri") == ONT_IRI for r in result)


async def test_mcp_list_ontologies_no_store():
    """store=None이면 빈 리스트."""
    init_services(None, None, None)
    result = await list_ontologies()
    assert result == []


# ── get_ontology_summary ───────────────────────────────────────────────────────

async def test_mcp_get_ontology_summary_empty(store):
    """빈 tbox → stats 0."""
    result = await get_ontology_summary(ONT_IRI)
    assert "ontology_id" in result
    assert "stats" in result
    assert result["ontology_id"] == ONT_IRI
    stats = result["stats"]
    assert stats["concepts"] == 0
    assert stats["individuals"] == 0


async def test_mcp_get_ontology_summary_with_data(populated_store):
    """tbox에 데이터 있을 때 stats 정확성."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await get_ontology_summary(ONT_IRI)
    stats = result["stats"]
    assert stats["concepts"] == 2
    assert stats["individuals"] == 1
    assert stats["object_properties"] == 1
    assert stats["data_properties"] == 1


async def test_mcp_get_ontology_summary_no_store():
    """store=None → error 반환."""
    init_services(None, None, None)
    result = await get_ontology_summary(ONT_IRI)
    assert "error" in result


# ── search_entities ────────────────────────────────────────────────────────────

async def test_mcp_search_entities_concept(populated_store):
    """kind='concept' → owl:Class 결과만 반환."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await search_entities(ONT_IRI, "Person", kind="concept")
    assert isinstance(result, list)
    assert all(r["kind"] == "concept" for r in result)
    iris = [r["iri"] for r in result]
    assert f"{ONT_IRI}#Person" in iris


@pytest.mark.xfail(
    reason="BUG-008: search_entities Individual 검색에 GRAPH 절 누락 — Named Graph 조회 불가",
    strict=True,
)
async def test_mcp_search_entities_all(populated_store):
    """kind='all' → Concept + Individual 혼합 (BUG-008: Individual 미반환)."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await search_entities(ONT_IRI, "", kind="all", limit=10)
    kinds = {r["kind"] for r in result}
    assert "concept" in kinds
    assert "individual" in kinds


async def test_mcp_search_entities_empty_query(populated_store):
    """빈 쿼리도 결과 반환 (전체 또는 IRI 포함 필터)."""
    init_services(populated_store, MagicMock(), MagicMock())
    # 빈 query는 CONTAINS가 항상 True → 전체 반환 가능
    result = await search_entities(ONT_IRI, "", kind="concept", limit=10)
    assert isinstance(result, list)


async def test_mcp_search_entities_no_match(populated_store):
    """매칭 없는 키워드 → 빈 리스트."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await search_entities(ONT_IRI, "XYZ_NOMATCH_12345", kind="all")
    assert result == []


async def test_mcp_search_entities_no_store():
    """store=None → 빈 리스트."""
    init_services(None, None, None)
    result = await search_entities(ONT_IRI, "Person")
    assert result == []


# ── search_relations ───────────────────────────────────────────────────────────

async def test_mcp_search_relations_all(populated_store):
    """query 없으면 ObjectProperty + DatatypeProperty 모두 반환."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await search_relations(ONT_IRI, query="")
    assert isinstance(result, list)
    assert len(result) >= 2
    kinds = {r["kind"] for r in result}
    assert "object" in kinds
    assert "data" in kinds


async def test_mcp_search_relations_keyword(populated_store):
    """'has' 포함 Property 필터."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await search_relations(ONT_IRI, query="has")
    iris = [r["iri"] for r in result]
    assert f"{ONT_IRI}#hasJob" in iris


async def test_mcp_search_relations_no_match(populated_store):
    """매칭 없는 키워드 → 빈 리스트."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await search_relations(ONT_IRI, query="NOMATCH_XYZ")
    assert result == []


async def test_mcp_search_relations_no_store():
    init_services(None, None, None)
    result = await search_relations(ONT_IRI)
    assert result == []


# ── get_subgraph ───────────────────────────────────────────────────────────────

async def test_mcp_get_subgraph_returns_nodes_edges(store, mock_graph_store):
    """graph_store.get_subgraph 결과를 그대로 반환."""
    init_services(store, mock_graph_store, MagicMock())
    result = await get_subgraph(ONT_IRI, [f"{ONT_IRI}#Person"])
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) >= 1


async def test_mcp_get_subgraph_depth_clamped(store, mock_graph_store):
    """depth=99 → 5로 클램핑."""
    init_services(store, mock_graph_store, MagicMock())
    await get_subgraph(ONT_IRI, [f"{ONT_IRI}#Person"], depth=99)
    mock_graph_store.get_subgraph.assert_called_once_with(
        ONT_IRI, [f"{ONT_IRI}#Person"], 5
    )


async def test_mcp_get_subgraph_no_store():
    init_services(None, None, None)
    result = await get_subgraph(ONT_IRI, [])
    assert "error" in result


# ── sparql_query ───────────────────────────────────────────────────────────────

async def test_mcp_sparql_query_select(populated_store):
    """SELECT 쿼리 → results 리스트 반환."""
    init_services(populated_store, MagicMock(), MagicMock())
    result = await sparql_query(
        ONT_IRI,
        f"PREFIX owl: <http://www.w3.org/2002/07/owl#> "
        f"SELECT ?c WHERE {{ GRAPH <{TBOX}> {{ ?c a owl:Class }} }}",
    )
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) >= 1


async def test_mcp_sparql_query_update_blocked(store):
    """UPDATE 쿼리 → 오류 반환 (실행 차단)."""
    init_services(store, MagicMock(), MagicMock())
    result = await sparql_query(
        ONT_IRI,
        f"INSERT DATA {{ GRAPH <{TBOX}> {{ <x:a> <x:b> <x:c> }} }}",
    )
    assert "error" in result
    assert "INSERT" in result["error"] or "not allowed" in result["error"].lower()


async def test_mcp_sparql_query_delete_blocked(store):
    """DELETE 쿼리 차단."""
    init_services(store, MagicMock(), MagicMock())
    result = await sparql_query(ONT_IRI, "DELETE DATA { <x:a> <x:b> <x:c> }")
    assert "error" in result


async def test_mcp_sparql_query_no_store():
    init_services(None, None, None)
    result = await sparql_query(ONT_IRI, "SELECT * WHERE { ?s ?p ?o }")
    assert "error" in result


# ── run_reasoner ───────────────────────────────────────────────────────────────

async def test_mcp_run_reasoner_consistent(store, mock_reasoner):
    """consistent=True 결과 반환."""
    init_services(store, MagicMock(), mock_reasoner)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await run_reasoner(ONT_IRI)
    assert result["consistent"] is True
    assert result["violations"] == []
    assert "inferred_axioms_count" in result
    assert result["job_id"] == "test-job-id"


async def test_mcp_run_reasoner_with_violations(store):
    """violations 포함 결과 반환."""
    reasoner = AsyncMock()
    reasoner.run.return_value = "job-with-violations"
    violation = MagicMock()
    violation.model_dump.return_value = {
        "type": "DisjointViolation",
        "subject_iri": f"{ONT_IRI}#alice",
        "description": "Disjoint class conflict",
    }
    result_obj = MagicMock()
    result_obj.consistent = False
    result_obj.violations = [violation]
    result_obj.inferred_axioms = []
    result_obj.execution_ms = 25
    reasoner.get_result.return_value = {"status": "completed", "result": result_obj}

    init_services(store, MagicMock(), reasoner)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await run_reasoner(ONT_IRI)

    assert result["consistent"] is False
    assert len(result["violations"]) == 1
    assert result["violations"][0]["type"] == "DisjointViolation"


async def test_mcp_run_reasoner_failed_job(store):
    """reasoner job이 failed 상태 → error 반환."""
    reasoner = AsyncMock()
    reasoner.run.return_value = "failed-job-id"
    reasoner.get_result.return_value = {
        "status": "failed",
        "error": "Out of memory",
    }
    init_services(store, MagicMock(), reasoner)
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await run_reasoner(ONT_IRI)
    assert result["status"] == "failed"
    assert "error" in result


async def test_mcp_run_reasoner_no_reasoner(store):
    """reasoner=None → error 반환."""
    init_services(store, None, None)
    result = await run_reasoner(ONT_IRI)
    assert "error" in result
