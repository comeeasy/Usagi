"""
Sync Worker — 주기 동기화 asyncio 태스크
"""
from __future__ import annotations

import asyncio
import logging

# TODO: import SyncService and OntologyStore
# from backend.services.sync_service import SyncService
# from backend.services.ontology_store import OntologyStore
# from backend.config import settings

logger = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 300  # 기본 5분


async def run_sync_worker() -> None:
    """
    무한 루프: SYNC_INTERVAL_SECONDS(기본 300초)마다 모든 온톨로지 full_sync 실행.
    asyncio.sleep으로 대기, CancelledError 시 graceful exit.
    """
    # TODO: implement
    # sync_service = SyncService()
    # while True:
    #     try:
    #         store = OntologyStore.get_instance()
    #         ontology_ids = await store.list_ontology_ids()
    #         for oid in ontology_ids:
    #             try:
    #                 result = await sync_service.full_sync(oid)
    #                 logger.info(f"Synced ontology {oid}: {result}")
    #             except Exception as e:
    #                 logger.error(f"Failed to sync ontology {oid}: {e}")
    #         await asyncio.sleep(SYNC_INTERVAL_SECONDS)
    #     except asyncio.CancelledError:
    #         logger.info("Sync worker cancelled, shutting down gracefully")
    #         break
    raise NotImplementedError
