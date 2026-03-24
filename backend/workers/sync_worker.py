"""Sync Worker — 주기 동기화 asyncio 태스크"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_sync_worker() -> None:
    """주기적으로 모든 온톨로지 full_sync 실행."""
    # Import here to avoid circular imports
    from config import settings

    interval = settings.sync_interval_seconds  # default 300
    logger.info("Sync worker started, interval=%ds", interval)

    try:
        while True:
            await asyncio.sleep(interval)
            # Sync is triggered per-ontology by kafka commands in production
            # Worker just logs heartbeat here; actual sync happens in kafka_worker
            logger.debug("Sync worker heartbeat")
    except asyncio.CancelledError:
        logger.info("Sync worker stopped")
