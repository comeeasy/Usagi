"""
main.py — FastAPI + FastMCP 앱 진입점

lifespan 컨텍스트 매니저를 통해:
  1. Oxigraph Store 초기화
  2. Neo4j 드라이버 연결
  3. 백그라운드 asyncio 태스크 시작 (sync_worker, kafka_worker)
  4. 앱 종료 시 리소스 정리

FastMCP 인스턴스는 /mcp 경로에 SSE transport로 마운트된다.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import ontologies, concepts, individuals, properties, search, subgraph
from api import sparql, import_, merge, reasoner, sources
from config import settings
from mcp import mcp_app
from workers.sync_worker import sync_worker
from workers.kafka_worker import kafka_worker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI 앱 생명주기 관리.

    구현 세부사항:
    - OntologyStore(settings.oxigraph_path) 초기화 → app.state.ontology_store에 저장
    - GraphStore(settings.neo4j_uri, ...) 초기화 → app.state.graph_store에 저장
    - asyncio.create_task(sync_worker()) 로 주기 동기화 시작
    - asyncio.create_task(kafka_worker()) 로 Kafka Consumer 시작
    - yield 이후 (종료 시):
        - 두 태스크에 cancel() 후 await (CancelledError 무시)
        - GraphStore.close() 호출 (Neo4j 드라이버 정리)
    """
    # TODO: OntologyStore 및 GraphStore 초기화
    # from services.ontology_store import OntologyStore
    # from services.graph_store import GraphStore
    # app.state.ontology_store = OntologyStore(settings.oxigraph_path)
    # app.state.graph_store = GraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    # TODO: 백그라운드 태스크 시작
    # sync_task = asyncio.create_task(sync_worker())
    # kafka_task = asyncio.create_task(kafka_worker())

    logger.info("Ontology Platform starting up...")

    yield

    # TODO: 종료 처리
    # sync_task.cancel()
    # kafka_task.cancel()
    # await asyncio.gather(sync_task, kafka_task, return_exceptions=True)
    # await app.state.graph_store.close()

    logger.info("Ontology Platform shut down.")


app = FastAPI(
    title="Ontology Platform API",
    description="Palantir Foundry 스타일 온톨로지 플랫폼 — REST API + MCP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어 — 개발 환경에서는 모든 오리진 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 운영 환경에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록 — prefix: /api/v1
API_PREFIX = "/api/v1"

# TODO: 각 라우터를 include_router로 등록
# app.include_router(ontologies.router, prefix=API_PREFIX)
# app.include_router(concepts.router, prefix=API_PREFIX)
# app.include_router(individuals.router, prefix=API_PREFIX)
# app.include_router(properties.router, prefix=API_PREFIX)
# app.include_router(search.router, prefix=API_PREFIX)
# app.include_router(subgraph.router, prefix=API_PREFIX)
# app.include_router(sparql.router, prefix=API_PREFIX)
# app.include_router(import_.router, prefix=API_PREFIX)
# app.include_router(merge.router, prefix=API_PREFIX)
# app.include_router(reasoner.router, prefix=API_PREFIX)
# app.include_router(sources.router, prefix=API_PREFIX)

# FastMCP SSE 마운트 — /mcp 경로
# TODO: app.mount("/mcp", mcp_app)


@app.get("/health")
async def health_check() -> dict:
    """헬스 체크 엔드포인트 — Nginx/컨테이너 헬스 프로브용."""
    return {"status": "ok"}
