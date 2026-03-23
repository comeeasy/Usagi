"""
Backing Source Pydantic models
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

SourceType = Literal["jdbc", "api-rest", "api-stream", "manual", "owl-file"]


class JDBCConfig(BaseModel):
    jdbc_url: str
    username: str
    password_secret: str      # 시크릿 참조 키
    query: str                # SELECT 쿼리 (PK 컬럼 포함 필수)
    primary_key_field: str
    poll_interval_seconds: int = 300


class APIConfig(BaseModel):
    url: str
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = {}
    auth_type: Literal["none", "bearer", "basic", "apikey"] = "none"
    auth_secret: str | None = None
    response_json_path: str             # 배열을 가리키는 JSONPath
    id_field: str
    poll_interval_seconds: int = 300


class StreamConfig(BaseModel):
    kafka_brokers: list[str]
    kafka_topic: str
    consumer_group: str
    id_field: str
    delivery_semantics: Literal["exactly-once", "at-least-once"] = "at-least-once"


class PropertyMapping(BaseModel):
    source_field: str           # 소스의 컬럼/필드 이름
    property_iri: str           # 대상 OWL Property IRI
    datatype: str | None = None # DataProperty인 경우 xsd:* 타입


class BackingSource(BaseModel):
    id: str
    ontology_id: str
    label: str
    source_type: SourceType
    concept_iri: str            # 이 소스가 채우는 Concept IRI
    iri_template: str           # IRI 생성 템플릿: "https://ex.org/emp/{emp_id}"
    property_mappings: list[PropertyMapping] = []
    conflict_policy: Literal["user-edit-wins", "latest-wins"] = "user-edit-wins"
    config: JDBCConfig | APIConfig | StreamConfig | dict[str, Any] = {}
    status: Literal["active", "paused", "error"] = "active"
    last_sync_at: str | None = None  # ISO 8601


class BackingSourceCreate(BaseModel):
    label: str
    source_type: SourceType
    concept_iri: str
    iri_template: str
    property_mappings: list[PropertyMapping] = []
    conflict_policy: Literal["user-edit-wins", "latest-wins"] = "user-edit-wins"
    config: JDBCConfig | APIConfig | StreamConfig | dict[str, Any] = {}


class BackingSourceUpdate(BaseModel):
    label: str | None = None
    concept_iri: str | None = None
    iri_template: str | None = None
    property_mappings: list[PropertyMapping] | None = None
    conflict_policy: Literal["user-edit-wins", "latest-wins"] | None = None
    config: JDBCConfig | APIConfig | StreamConfig | dict[str, Any] | None = None
    status: Literal["active", "paused", "error"] | None = None


class SourceEvent(BaseModel):
    """Kafka raw-source-events 메시지 구조."""
    source_id: str
    ontology_id: str
    event_type: Literal["upsert", "delete"]
    timestamp: str   # ISO 8601
    records: list[dict[str, Any]]
