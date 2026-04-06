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


class PropertyValue(BaseModel):
    """임의 predicate-value 쌍 — 구조화 필드에 해당하지 않는 모든 트리플"""
    predicate: str
    value: str
    value_type: Literal["uri", "literal"] = "literal"
    datatype: str | None = None   # xsd 타입 (literal일 때)
    language: str | None = None   # 언어 태그 (literal일 때)


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
    subclass_count: int = 0               # 직계 하위 클래스 수 (트리 toggle 여부 판단)
    properties: list[PropertyValue] = []  # 위에 해당하지 않는 임의 트리플


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
