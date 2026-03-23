"""
Kafka Producer — raw-source-events 및 sync-commands 토픽 발행
"""
from __future__ import annotations

import json
import logging
from typing import Any

# TODO: import kafka-python
# from kafka import KafkaProducer as _KafkaProducer

logger = logging.getLogger(__name__)

TOPIC_RAW_SOURCE_EVENTS = "raw-source-events"
TOPIC_SYNC_COMMANDS = "sync-commands"


class KafkaProducer:
    """Kafka 토픽에 이벤트를 발행하는 프로듀서."""

    def __init__(self, bootstrap_servers: str = "localhost:9092") -> None:
        self.bootstrap_servers = bootstrap_servers
        self._producer = None

    def _get_producer(self):
        # TODO: lazy init
        # if self._producer is None:
        #     self._producer = _KafkaProducer(
        #         bootstrap_servers=self.bootstrap_servers,
        #         value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        #         key_serializer=lambda k: k.encode("utf-8") if k else None,
        #     )
        # return self._producer
        raise NotImplementedError

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

        Args:
            source_id: 소스 ID (파티션 키로 사용)
            ontology_id: 대상 온톨로지 ID
            event_type: 이벤트 타입 ('insert' | 'update' | 'delete')
            records: 변환할 레코드 목록
        """
        # TODO: implement
        # payload = {
        #     "source_id": source_id,
        #     "ontology_id": ontology_id,
        #     "event_type": event_type,
        #     "records": records,
        # }
        # producer = self._get_producer()
        # producer.send(TOPIC_RAW_SOURCE_EVENTS, key=source_id, value=payload)
        # producer.flush()
        raise NotImplementedError

    async def publish_sync_command(self, ontology_id: str) -> None:
        """
        sync-commands 토픽에 동기화 트리거 메시지 발행.

        Args:
            ontology_id: 동기화할 온톨로지 ID
        """
        # TODO: implement
        # payload = {"ontology_id": ontology_id, "command": "full_sync"}
        # producer = self._get_producer()
        # producer.send(TOPIC_SYNC_COMMANDS, key=ontology_id, value=payload)
        # producer.flush()
        raise NotImplementedError
