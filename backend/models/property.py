"""
Property Pydantic models
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

XSDDatatype = Literal[
    "xsd:string",
    "xsd:integer",
    "xsd:decimal",
    "xsd:float",
    "xsd:double",
    "xsd:boolean",
    "xsd:date",
    "xsd:dateTime",
    "xsd:anyURI",
    "xsd:langString",
]

ObjectPropertyCharacteristic = Literal[
    "Functional",
    "InverseFunctional",
    "Transitive",
    "Symmetric",
    "Asymmetric",
    "Reflexive",
    "Irreflexive",
]


class ObjectProperty(BaseModel):
    iri: str
    ontology_id: str
    label: str
    comment: str | None = None
    domain: list[str] = []             # Concept IRI 목록
    range: list[str] = []              # Concept IRI 목록
    super_properties: list[str] = []   # rdfs:subPropertyOf
    inverse_of: str | None = None      # owl:inverseOf
    characteristics: list[ObjectPropertyCharacteristic] = []


class DataProperty(BaseModel):
    iri: str
    ontology_id: str
    label: str
    comment: str | None = None
    domain: list[str] = []             # Concept IRI 목록
    range: list[XSDDatatype] = []      # xsd:* 타입 목록
    super_properties: list[str] = []
    is_functional: bool = False


class ObjectPropertyCreate(BaseModel):
    iri: str
    label: str
    comment: str | None = None
    domain: list[str] = []
    range: list[str] = []
    super_properties: list[str] = []
    inverse_of: str | None = None
    characteristics: list[ObjectPropertyCharacteristic] = []


class DataPropertyCreate(BaseModel):
    iri: str
    label: str
    comment: str | None = None
    domain: list[str] = []
    range: list[XSDDatatype] = []
    super_properties: list[str] = []
    is_functional: bool = False


class ObjectPropertyUpdate(BaseModel):
    label: str | None = None
    comment: str | None = None
    domain: list[str] | None = None
    range: list[str] | None = None
    super_properties: list[str] | None = None
    inverse_of: str | None = None
    characteristics: list[ObjectPropertyCharacteristic] | None = None


class DataPropertyUpdate(BaseModel):
    label: str | None = None
    comment: str | None = None
    domain: list[str] | None = None
    range: list[XSDDatatype] | None = None
    super_properties: list[str] | None = None
    is_functional: bool | None = None
