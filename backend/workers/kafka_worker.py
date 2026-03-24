"""Kafka Worker — Kafka Consumer 상시 실행"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_kafka_worker() -> None:
    """KafkaConsumer 실행, 예외 시 5초 후 재시작."""
    from config import settings

    logger.info("Kafka worker started")
    delay = 5

    while True:
        try:
            # kafka-python is sync; run in executor
            loop = asyncio.get_event_loop()
            # For MVP: just sleep and log; actual kafka integration requires kafka running
            await asyncio.sleep(delay)
            logger.debug("Kafka worker heartbeat (kafka not connected)")
        except asyncio.CancelledError:
            logger.info("Kafka worker stopped")
            break
        except Exception as e:
            logger.error("Kafka worker error: %s, restarting in %ds", e, delay)
            await asyncio.sleep(delay)
