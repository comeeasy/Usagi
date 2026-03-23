"""
Individual Pydantic models
"""
from __future__ import annotations

from pydantic import BaseModel


class DataPropertyValue(BaseModel):
    property_iri: str
    value: str
    datatype: str          # xsd:string, xsd:integer, xsd:dateTime 등
    graph_iri: str


class ObjectPropertyValue(BaseModel):
    property_iri: str
    target_iri: str
    graph_iri: str


class ProvenanceRecord(BaseModel):
    graph_iri: str         # Named Graph IRI
    source_id: str         # BackingSource.id
    source_type: str       # SourceType
    ingested_at: str       # ISO 8601
    triple_count: int


class Individual(BaseModel):
    iri: str
    ontology_id: str
    label: str | None = None
    types: list[str] = []                              # rdf:type 대상 Concept IRI 목록
    data_property_values: list[DataPropertyValue] = []
    object_property_values: list[ObjectPropertyValue] = []
    same_as: list[str] = []                            # owl:sameAs
    different_from: list[str] = []                     # owl:differentFrom
    provenance: list[ProvenanceRecord] = []


class IndividualCreate(BaseModel):
    iri: str
    label: str | None = None
    types: list[str] = []
    data_property_values: list[DataPropertyValue] = []
    object_property_values: list[ObjectPropertyValue] = []
    same_as: list[str] = []
    different_from: list[str] = []


class IndividualUpdate(BaseModel):
    label: str | None = None
    types: list[str] | None = None
    data_property_values: list[DataPropertyValue] | None = None
    object_property_values: list[ObjectPropertyValue] | None = None
    same_as: list[str] | None = None
    different_from: list[str] | None = None
