"""
Backing Source Pydantic models
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

SourceType = Literal["jdbc", "api", "stream", "file"]


class JDBCConfig(BaseModel):
    url: str
    driver: str
    username: str
    password: str
    query: str
    batch_size: int = 1000


class APIConfig(BaseModel):
    endpoint: str
    method: Literal["GET", "POST"] = "GET"
    headers: dict[str, str] = {}
    params: dict[str, Any] = {}
    auth_type: Literal["none", "bearer", "basic", "api_key"] = "none"
    auth_token: str | None = None
    pagination_type: Literal["none", "page", "cursor", "offset"] = "none"
    records_path: str | None = None  # JSONPath to records array


class StreamConfig(BaseModel):
    bootstrap_servers: str
    topic: str
    consumer_group: str
    schema_registry_url: str | None = None
    value_format: Literal["json", "avro", "protobuf"] = "json"


class PropertyMapping(BaseModel):
    source_field: str
    property_iri: str
    property_type: Literal["data", "object"]
    datatype: str | None = None
    language: str | None = None
    transform: str | None = None  # 선택적 변환 표현식


class BackingSource(BaseModel):
    id: str
    ontology_id: str
    name: str
    source_type: SourceType
    concept_iri: str
    iri_template: str
    property_mappings: list[PropertyMapping] = []
    jdbc_config: JDBCConfig | None = None
    api_config: APIConfig | None = None
    stream_config: StreamConfig | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None = None


class BackingSourceCreate(BaseModel):
    name: str
    source_type: SourceType
    concept_iri: str
    iri_template: str
    property_mappings: list[PropertyMapping] = []
    jdbc_config: JDBCConfig | None = None
    api_config: APIConfig | None = None
    stream_config: StreamConfig | None = None


class BackingSourceUpdate(BaseModel):
    name: str | None = None
    concept_iri: str | None = None
    iri_template: str | None = None
    property_mappings: list[PropertyMapping] | None = None
    jdbc_config: JDBCConfig | None = None
    api_config: APIConfig | None = None
    stream_config: StreamConfig | None = None
    is_active: bool | None = None


class SourceEvent(BaseModel):
    """Kafka raw-source-events 메시지 구조."""

    source_id: str
    ontology_id: str
    event_type: Literal["insert", "update", "delete"]
    records: list[dict[str, Any]]
    timestamp: str  # ISO 8601
