"""
pytest fixtures for ontology platform tests.

테스트 전략:
  - OntologyStore: AsyncMock (Fuseki 없이 단위 테스트)
  - KafkaProducer: MagicMock — Kafka 없이 테스트
  - FastAPI 테스트 앱: 프로덕션 lifespan 대신 테스트 lifespan으로 state 주입

  Fuseki가 필요한 통합 테스트는 @pytest.mark.integration 마커로 분리.
  실행: pytest -m integration (Fuseki 실행 중일 때)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, ASGITransport

from services.ontology_store import OntologyStore
from services.reasoner_service import ReasonerService
from services.merge_service import MergeService
from services.ingestion.kafka_producer import KafkaProducer


# ── In-Memory OntologyStore (rdflib 기반) ─────────────────────────────────────

class MemoryOntologyStore:
    """
    rdflib.ConjunctiveGraph 기반 인메모리 OntologyStore.
    Fuseki 없이 SPARQL SELECT / ASK / UPDATE를 지원하는 테스트 전용 구현.
    """

    def __init__(self):
        import rdflib
        self._graph = rdflib.ConjunctiveGraph()

    @staticmethod
    def _term_to_dict(term) -> dict:
        import rdflib
        if isinstance(term, rdflib.URIRef):
            return {"type": "uri", "value": str(term)}
        if isinstance(term, rdflib.BNode):
            return {"type": "bnode", "value": str(term)}
        if isinstance(term, rdflib.Literal):
            result: dict = {"type": "literal", "value": str(term)}
            if term.datatype:
                result["datatype"] = str(term.datatype)
            if term.language:
                result["xml:lang"] = term.language
            return result
        return {"type": "literal", "value": str(term)}

    async def sparql_select(self, query: str, dataset=None) -> list[dict]:
        results = self._graph.query(query)
        rows = []
        for row in results:
            d = {}
            for var in results.vars:
                val = row[var]
                if val is not None:
                    d[str(var)] = self._term_to_dict(val)
            rows.append(d)
        return rows

    async def sparql_ask(self, query: str, dataset=None) -> bool:
        result = self._graph.query(query)
        return bool(result.askAnswer)

    async def sparql_update(self, update: str, dataset=None) -> None:
        self._graph.update(update)

    async def sparql_construct(self, query: str, dataset=None):
        from services.ontology_store import Triple
        import rdflib
        result = self._graph.query(query)
        return [Triple(subject=s, predicate=p, object_=o) for s, p, o in result]

    async def insert_triples(self, graph_iri: str, triples, dataset=None) -> None:
        from services.ontology_store import _term_to_sparql
        import rdflib
        lines = [
            f"{_term_to_sparql(t.subject)} {_term_to_sparql(t.predicate)} {_term_to_sparql(t.object_)} ."
            for t in triples
        ]
        update = f"INSERT DATA {{ GRAPH <{graph_iri}> {{\n" + "\n".join(lines) + "\n} }"
        self._graph.update(update)

    async def delete_graph(self, graph_iri: str, dataset=None) -> None:
        self._graph.update(f"DROP SILENT GRAPH <{graph_iri}>")

    async def export_turtle(self, graph_iri: str, dataset=None) -> str:
        import rdflib
        g = self._graph.get_context(rdflib.URIRef(graph_iri))
        return g.serialize(format="turtle")

    async def put_graph_turtle(self, graph_iri: str, turtle, dataset=None) -> None:
        import rdflib
        await self.delete_graph(graph_iri)
        body = turtle if isinstance(turtle, str) else turtle.decode("utf-8")
        self._graph.parse(data=body, format="turtle", publicID=rdflib.URIRef(graph_iri))

    async def close(self) -> None:
        pass


# ── 서비스 Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def ontology_store():
    """OntologyStore AsyncMock — Fuseki 없이 단위 테스트."""
    mock = AsyncMock(spec=OntologyStore)
    mock.sparql_select.return_value = []
    mock.sparql_ask.return_value = False
    mock.sparql_update.return_value = None
    mock.sparql_construct.return_value = []
    mock.insert_triples.return_value = None
    mock.delete_graph.return_value = None
    mock.list_ontologies.return_value = ([], 0)
    mock.get_ontology_stats.return_value = {
        "concepts": 0, "individuals": 0,
        "object_properties": 0, "data_properties": 0, "named_graphs": 0,
    }
    mock.close.return_value = None
    return mock


@pytest.fixture
def mock_kafka_producer():
    """Kafka KafkaProducer Mock."""
    mock = MagicMock(spec=KafkaProducer)
    mock.publish_sync_command = AsyncMock(return_value=None)
    mock.close.return_value = None
    return mock


# ── 테스트 FastAPI 앱 ──────────────────────────────────────────────────────────

@pytest.fixture
def app(ontology_store, mock_kafka_producer):
    """
    테스트용 FastAPI 앱.

    ASGITransport은 lifespan을 트리거하지 않으므로, lifespan 없이 state를
    직접 앱 객체에 주입한다. 라우터는 각 테스트마다 새 앱 인스턴스에 등록된다.
    """
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # state 직접 주입 — lifespan 없이도 request.app.state.xxx 접근 가능
    test_app.state.ontology_store = ontology_store
    test_app.state.reasoner_service = ReasonerService(ontology_store)
    test_app.state.merge_service = MergeService(ontology_store)
    test_app.state.kafka_producer = mock_kafka_producer

    from api import ontologies, concepts, individuals, properties, search, subgraph
    from api import sparql, import_, merge, reasoner, sources, graphs

    API = "/api/v1"
    test_app.include_router(ontologies.router, prefix=API)
    test_app.include_router(concepts.router, prefix=API)
    test_app.include_router(individuals.router, prefix=API)
    test_app.include_router(properties.router, prefix=API)
    test_app.include_router(search.router, prefix=API)
    test_app.include_router(subgraph.router, prefix=API)
    test_app.include_router(sparql.router, prefix=API)
    test_app.include_router(import_.router, prefix=API)
    test_app.include_router(merge.router, prefix=API)
    test_app.include_router(reasoner.router, prefix=API)
    test_app.include_router(sources.router, prefix=API)
    test_app.include_router(graphs.router, prefix=API)

    return test_app


@pytest_asyncio.fixture
async def client(app):
    """httpx AsyncClient — 실제 HTTP 요청으로 FastAPI 엔드포인트 테스트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test/api/v1",
    ) as ac:
        yield ac


# ── 공통 테스트 데이터 ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_ontology() -> dict:
    """테스트용 온톨로지 생성 페이로드."""
    return {
        "label": "Test Ontology",
        "iri": "https://test.example.org/ontology",
        "description": "A test ontology for unit tests",
        "version": "1.0.0",
    }


@pytest_asyncio.fixture
async def created_ontology(client: AsyncClient, sample_ontology: dict) -> dict:
    """온톨로지를 미리 생성해두는 fixture — Concept/Individual 테스트의 선행 조건."""
    resp = await client.post("/ontologies", json=sample_ontology)
    assert resp.status_code == 201, f"Ontology creation failed: {resp.text}"
    return resp.json()
