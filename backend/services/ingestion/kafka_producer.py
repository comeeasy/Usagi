"""Kafka Producer — raw-source-events 및 sync-commands 토픽 발행"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

try:
    from kafka import KafkaProducer as _KafkaProducer
    _KAFKA_AVAILABLE = True
except ImportError:
    _KafkaProducer = None  # type: ignore
    _KAFKA_AVAILABLE = False

logger = logging.getLogger(__name__)

TOPIC_RAW_SOURCE_EVENTS = "raw-source-events"
TOPIC_SYNC_COMMANDS = "sync-commands"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class KafkaProducer:
    """Kafka 토픽에 이벤트를 발행하는 프로듀서."""

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        self.bootstrap_servers = bootstrap_servers
        self._producer: Any = None

    def _get_producer(self) -> Any:
        """Lazy init: 첫 호출 시 KafkaProducer 인스턴스 생성."""
        if self._producer is None:
            if not _KAFKA_AVAILABLE:
                raise RuntimeError("kafka-python is not installed")
            self._producer = _KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
        return self._producer

    async def publish_source_event(
        self,
        source_id: str,
        ontology_id: str,
        event_type: str,
        records: list[dict[str, Any]],
    ) -> None:
        """
        raw-source-events 토픽에 JSON 직렬화하여 발행.
        파티션 키: source_id
        """
        payload = {
            "source_id": source_id,
            "ontology_id": ontology_id,
            "event_type": event_type,
            "timestamp": _now_iso(),
            "records": records,
        }

        def _send() -> None:
            producer = self._get_producer()
            producer.send(TOPIC_RAW_SOURCE_EVENTS, key=source_id, value=payload)
            producer.flush()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send)
        except Exception as exc:
            logger.error("Failed to publish source event: %s", exc)
            raise

    async def publish_sync_command(
        self,
        source_id: str,
        trigger_type: str = "manual",
    ) -> None:
        """
        sync-commands 토픽에 동기화 트리거 메시지 발행.
        """
        payload = {
            "source_id": source_id,
            "trigger_type": trigger_type,
            "triggered_at": _now_iso(),
        }

        def _send() -> None:
            producer = self._get_producer()
            producer.send(TOPIC_SYNC_COMMANDS, key=source_id, value=payload)
            producer.flush()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send)
        except Exception as exc:
            logger.error("Failed to publish sync command: %s", exc)
            raise

    def close(self) -> None:
        """프로듀서 종료."""
        if self._producer is not None:
            try:
                self._producer.close()
            except Exception as exc:
                logger.error("Error closing KafkaProducer: %s", exc)
            finally:
                self._producer = None
