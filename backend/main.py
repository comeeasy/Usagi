"""
main.py — FastAPI + FastMCP 앱 진입점
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from services.ontology_store import OntologyStore
from services.graph_store import GraphStore
from services.reasoner_service import ReasonerService
from services.merge_service import MergeService
from services.vector_index import VectorIndexManager
from services.ingestion.kafka_producer import KafkaProducer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Ontology Platform starting up...")

    # 스토어 초기화
    app.state.ontology_store = OntologyStore(settings.oxigraph_path)
    app.state.graph_store = GraphStore(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
    )
    app.state.reasoner_service = ReasonerService(app.state.ontology_store)
    app.state.merge_service = MergeService(app.state.ontology_store)
    app.state.vector_index_manager = VectorIndexManager()
    app.state.kafka_producer = KafkaProducer(settings.kafka_brokers)

    # MCP 서비스 등록
    from app_mcp.tools import init_services as _init_mcp_services
    _init_mcp_services(
        app.state.ontology_store,
        app.state.graph_store,
        app.state.reasoner_service,
    )

    # 백그라운드 태스크
    from workers.sync_worker import run_sync_worker
    from workers.kafka_worker import run_kafka_worker

    sync_task = asyncio.create_task(run_sync_worker())
    kafka_task = asyncio.create_task(run_kafka_worker())

    yield

    # 종료 처리
    sync_task.cancel()
    kafka_task.cancel()
    await asyncio.gather(sync_task, kafka_task, return_exceptions=True)
    app.state.kafka_producer.close()
    await app.state.graph_store.close()

    logger.info("Ontology Platform shut down.")


app = FastAPI(
    title="Ontology Platform API",
    description="Palantir Foundry 스타일 온톨로지 플랫폼 — REST API + MCP",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

from api import ontologies, concepts, individuals, properties, search, subgraph
from api import sparql, import_, merge, reasoner, sources

app.include_router(ontologies.router, prefix=API_PREFIX)
app.include_router(concepts.router, prefix=API_PREFIX)
app.include_router(individuals.router, prefix=API_PREFIX)
app.include_router(properties.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(subgraph.router, prefix=API_PREFIX)
app.include_router(sparql.router, prefix=API_PREFIX)
app.include_router(import_.router, prefix=API_PREFIX)
app.include_router(merge.router, prefix=API_PREFIX)
app.include_router(reasoner.router, prefix=API_PREFIX)
app.include_router(sources.router, prefix=API_PREFIX)

from app_mcp.tools import mcp

app.mount("/mcp", mcp.http_app(transport="sse"))

# 업로드된 CSV 파일 정적 서빙 (Neo4j LOAD CSV 접근용)
_UPLOADS_DIR = Path("uploads")
_UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
