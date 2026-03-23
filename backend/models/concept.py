"""
Concept Pydantic models
"""
from __future__ import annotations

from pydantic import BaseModel


class PropertyRestriction(BaseModel):
    property_iri: str
    restriction_type: str  # 'some' | 'all' | 'exactly' | 'min' | 'max'
    cardinality: int | None = None
    filler_iri: str | None = None


class Concept(BaseModel):
    iri: str
    label: str | None = None
    comment: str | None = None
    ontology_id: str
    parent_iris: list[str] = []
    restrictions: list[PropertyRestriction] = []
    is_deprecated: bool = False


class ConceptCreate(BaseModel):
    iri: str
    label: str | None = None
    comment: str | None = None
    parent_iris: list[str] = []
    restrictions: list[PropertyRestriction] = []


class ConceptUpdate(BaseModel):
    label: str | None = None
    comment: str | None = None
    parent_iris: list[str] | None = None
    restrictions: list[PropertyRestriction] | None = None
    is_deprecated: bool | None = None
