"""
Concept Pydantic models
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class PropertyRestriction(BaseModel):
    property_iri: str
    type: Literal[
        "someValuesFrom",
        "allValuesFrom",
        "hasValue",
        "minCardinality",
        "maxCardinality",
        "exactCardinality",
    ]
    value: str          # 클래스 IRI 또는 리터럴 값
    cardinality: int | None = None


class Concept(BaseModel):
    iri: str
    ontology_id: str
    label: str
    comment: str | None = None
    super_classes: list[str] = []         # rdfs:subClassOf 대상 IRI 목록
    equivalent_classes: list[str] = []    # owl:equivalentClass
    disjoint_with: list[str] = []         # owl:disjointWith
    restrictions: list[PropertyRestriction] = []
    individual_count: int = 0


class ConceptCreate(BaseModel):
    iri: str
    label: str
    comment: str | None = None
    super_classes: list[str] = []
    equivalent_classes: list[str] = []
    disjoint_with: list[str] = []
    restrictions: list[PropertyRestriction] = []


class ConceptUpdate(BaseModel):
    label: str | None = None
    comment: str | None = None
    super_classes: list[str] | None = None
    equivalent_classes: list[str] | None = None
    disjoint_with: list[str] | None = None
    restrictions: list[PropertyRestriction] | None = None
