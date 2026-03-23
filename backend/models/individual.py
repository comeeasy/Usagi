"""
Individual Pydantic models
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DataPropertyValue(BaseModel):
    property_iri: str
    value: Any
    datatype: str | None = None
    language: str | None = None


class ObjectPropertyValue(BaseModel):
    property_iri: str
    target_iri: str


class ProvenanceRecord(BaseModel):
    source_id: str
    source_type: str
    generated_at: datetime
    record_id: str | None = None
    named_graph_iri: str | None = None


class Individual(BaseModel):
    iri: str
    label: str | None = None
    ontology_id: str
    type_iris: list[str] = []
    data_properties: list[DataPropertyValue] = []
    object_properties: list[ObjectPropertyValue] = []
    provenance: list[ProvenanceRecord] = []


class IndividualCreate(BaseModel):
    iri: str
    label: str | None = None
    type_iris: list[str] = []
    data_properties: list[DataPropertyValue] = []
    object_properties: list[ObjectPropertyValue] = []


class IndividualUpdate(BaseModel):
    label: str | None = None
    type_iris: list[str] | None = None
    data_properties: list[DataPropertyValue] | None = None
    object_properties: list[ObjectPropertyValue] | None = None
