"""
Kafka Worker — Kafka Consumer 상시 실행
"""
from __future__ import annotations

import asyncio
import logging

# TODO: import KafkaConsumer
# from backend.services.ingestion.kafka_consumer import KafkaConsumer
# from backend.config import settings

logger = logging.getLogger(__name__)

RESTART_DELAY_SECONDS = 5


async def run_kafka_worker() -> None:
    """
    KafkaConsumer 인스턴스 생성 후 consume_loop 실행.
    예외 발생 시 5초 후 재시작 (지수 백오프 미적용 — 단순 재시작).
    """
    # TODO: implement
    # while True:
    #     consumer = KafkaConsumer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
    #     try:
    #         await consumer.start()
    #         logger.info("Kafka consumer started")
    #         await consumer.consume_loop()
    #     except asyncio.CancelledError:
    #         logger.info("Kafka worker cancelled, shutting down")
    #         await consumer.stop()
    #         break
    #     except Exception as e:
    #         logger.error(f"Kafka consumer error: {e}, restarting in {RESTART_DELAY_SECONDS}s")
    #         await consumer.stop()
    #         await asyncio.sleep(RESTART_DELAY_SECONDS)
    raise NotImplementedError
