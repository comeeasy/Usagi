"""Kafka Consumer — raw-source-events 토픽 소비 후 OntologyStore에 저장"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

try:
    from kafka import KafkaConsumer as _KafkaConsumer
    _KAFKA_AVAILABLE = True
except ImportError:
    _KafkaConsumer = None  # type: ignore
    _KAFKA_AVAILABLE = False

from services.ingestion.rdf_transformer import RDFTransformer
from services.ontology_graph import resolve_kg_graph_iri

logger = logging.getLogger(__name__)

TOPIC_RAW_SOURCE_EVENTS = "raw-source-events"


class KafkaConsumer:
    """Kafka raw-source-events 토픽을 소비하여 Oxigraph에 저장."""

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        self.bootstrap_servers = bootstrap_servers
        self._consumer: Any = None
        self._running = False
        self._store: Any = None
        self._source_registry: dict[str, Any] = {}
        self._transformer = RDFTransformer()

    def start(self, store: Any, source_registry: dict[str, Any]) -> None:
        """
        KafkaConsumer 초기화, raw-source-events 토픽 구독.

        Args:
            store: OntologyStore 인스턴스
            source_registry: {source_id: BackingSource} 딕셔너리
        """
        if not _KAFKA_AVAILABLE:
            logger.warning("kafka-python not available; KafkaConsumer will not start")
            return

        self._store = store
        self._source_registry = source_registry
        self._consumer = _KafkaConsumer(
            TOPIC_RAW_SOURCE_EVENTS,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="ontology-platform-consumer",
        )
        self._running = True
        logger.info("KafkaConsumer started, subscribed to %s", TOPIC_RAW_SOURCE_EVENTS)

    async def consume_loop(self) -> None:
        """무한 루프로 메시지 폴링, RDFTransformer 호출 후 OntologyStore에 저장."""
        if not _KAFKA_AVAILABLE or self._consumer is None:
            logger.warning("KafkaConsumer not initialized; consume_loop is a no-op")
            return

        loop = asyncio.get_event_loop()

        while self._running:
            # Run blocking poll in executor
            try:
                messages = await loop.run_in_executor(
                    None, lambda: self._consumer.poll(timeout_ms=1000)
                )
            except Exception as exc:
                logger.error("Error polling Kafka: %s", exc)
                await asyncio.sleep(1)
                continue

            for _tp, records in messages.items():
                for msg in records:
                    await self._process_message(msg.value)

            # Yield control to the event loop
            await asyncio.sleep(0)

    async def _process_message(self, data: dict) -> None:
        """단일 메시지 처리: RDF 변환 후 OntologyStore에 저장."""
        try:
            source_id = data.get("source_id", "")
            timestamp = data.get("timestamp", "")

            source = self._source_registry.get(source_id)
            if source is None:
                logger.warning("Unknown source_id=%s; skipping message", source_id)
                return

            # Build SourceEvent from raw data
            from models.source import SourceEvent
            event = SourceEvent(
                source_id=source_id,
                ontology_id=data.get("ontology_id", ""),
                event_type=data.get("event_type", "upsert"),
                timestamp=timestamp,
                records=data.get("records", []),
            )

            triples = self._transformer.transform(event, source)
            if triples:
                ont_uuid = event.ontology_id or ""
                graph_iri = await resolve_kg_graph_iri(self._store, ont_uuid, dataset=None)
                if not graph_iri:
                    logger.warning(
                        "Ontology not found for ontology_id=%s; skipping %d triples",
                        ont_uuid, len(triples),
                    )
                    return
                await self._store.insert_triples(graph_iri, triples)
                logger.debug(
                    "Inserted %d triples for source=%s into graph=%s",
                    len(triples), source_id, graph_iri,
                )

        except Exception as exc:
            logger.error("Error processing Kafka message: %s", exc)

    def stop(self) -> None:
        """컨슈머 graceful shutdown."""
        self._running = False
        if self._consumer is not None:
            try:
                self._consumer.close()
            except Exception as exc:
                logger.error("Error closing KafkaConsumer: %s", exc)
            finally:
                self._consumer = None
        logger.info("KafkaConsumer stopped")
