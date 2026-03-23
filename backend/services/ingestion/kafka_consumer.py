"""
Kafka Consumer — rdf-triples 토픽 소비 후 OntologyStore에 저장
"""
from __future__ import annotations

import asyncio
import logging

# TODO: import kafka-python and internal services
# from kafka import KafkaConsumer as _KafkaConsumer
# from backend.services.ontology_store import OntologyStore
# from backend.services.ingestion.rdf_transformer import RDFTransformer

logger = logging.getLogger(__name__)

TOPIC_RDF_TRIPLES = "rdf-triples"


class KafkaConsumer:
    """Kafka rdf-triples 토픽을 소비하여 Oxigraph에 저장."""

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        self.bootstrap_servers = bootstrap_servers
        self._consumer = None
        self._running = False

    async def start(self) -> None:
        """
        kafka-python KafkaConsumer 초기화, rdf-triples 토픽 구독.
        """
        # TODO: implement
        # self._consumer = _KafkaConsumer(
        #     TOPIC_RDF_TRIPLES,
        #     bootstrap_servers=self.bootstrap_servers,
        #     value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        #     auto_offset_reset="earliest",
        #     enable_auto_commit=True,
        # )
        # self._running = True
        raise NotImplementedError

    async def consume_loop(self) -> None:
        """
        무한 루프로 메시지 폴링, rdf_transformer 호출 후 OntologyStore에 저장.
        """
        # TODO: implement
        # transformer = RDFTransformer()
        # store = OntologyStore.get_instance()
        # while self._running:
        #     messages = self._consumer.poll(timeout_ms=1000)
        #     for tp, records in messages.items():
        #         for record in records:
        #             triples = transformer.transform(record.value)
        #             await store.insert_triples(record.value["ontology_id"], triples)
        #     await asyncio.sleep(0)
        raise NotImplementedError

    async def stop(self) -> None:
        """
        컨슈머 graceful shutdown.
        """
        # TODO: implement
        # self._running = False
        # if self._consumer:
        #     self._consumer.close()
        #     self._consumer = None
        # logger.info("KafkaConsumer stopped")
        raise NotImplementedError
