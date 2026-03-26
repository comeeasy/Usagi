"""
pytest fixtures for ontology platform tests.

테스트 전략:
  - OntologyStore: pyoxigraph 인메모리 Store (path=None) — 실제 SPARQL 동작 검증
  - GraphStore: AsyncMock — Neo4j 없이 테스트
  - KafkaProducer: MagicMock — Kafka 없이 테스트
  - FastAPI 테스트 앱: 프로덕션 lifespan 대신 테스트 lifespan으로 state 주입
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, ASGITransport

from services.ontology_store import OntologyStore
from services.graph_store import GraphStore
from services.reasoner_service import ReasonerService
from services.merge_service import MergeService
from services.ingestion.kafka_producer import KafkaProducer


# ── 서비스 Fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def ontology_store():
    """인메모리 Oxigraph OntologyStore — 각 테스트마다 새 인스턴스."""
    return OntologyStore(path=None)


@pytest.fixture
def mock_graph_store():
    """Neo4j GraphStore Mock — 실제 DB 연결 없음."""
    mock = AsyncMock(spec=GraphStore)
    mock.get_subgraph.return_value = {"nodes": [], "edges": []}
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
def app(ontology_store, mock_graph_store, mock_kafka_producer):
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
    test_app.state.graph_store = mock_graph_store
    test_app.state.reasoner_service = ReasonerService(ontology_store)
    test_app.state.merge_service = MergeService(ontology_store)
    test_app.state.kafka_producer = mock_kafka_producer

    from api import ontologies, concepts, individuals, properties, search, subgraph
    from api import sparql, import_, merge, reasoner, sources

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
