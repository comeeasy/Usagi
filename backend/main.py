"""
main.py — FastAPI + FastMCP 앱 진입점
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services.ontology_store import OntologyStore
from services.graph_store import GraphStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Ontology Platform starting up...")

    # 스토어 초기화
    app.state.ontology_store = OntologyStore(settings.oxigraph_path)
    app.state.graph_store = GraphStore(
        settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
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

from mcp.tools import mcp

app.mount("/mcp", mcp.get_asgi_app())


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
