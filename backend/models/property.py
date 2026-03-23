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
]

ObjectPropertyCharacteristic = Literal[
    "functional",
    "inverseFunctional",
    "transitive",
    "symmetric",
    "asymmetric",
    "reflexive",
    "irreflexive",
]


class ObjectProperty(BaseModel):
    iri: str
    label: str | None = None
    comment: str | None = None
    ontology_id: str
    domain_iri: str | None = None
    range_iri: str | None = None
    characteristics: list[ObjectPropertyCharacteristic] = []
    inverse_of: str | None = None
    is_deprecated: bool = False


class DataProperty(BaseModel):
    iri: str
    label: str | None = None
    comment: str | None = None
    ontology_id: str
    domain_iri: str | None = None
    range_datatype: XSDDatatype | None = None
    is_functional: bool = False
    is_deprecated: bool = False


class ObjectPropertyCreate(BaseModel):
    iri: str
    label: str | None = None
    comment: str | None = None
    domain_iri: str | None = None
    range_iri: str | None = None
    characteristics: list[ObjectPropertyCharacteristic] = []
    inverse_of: str | None = None


class DataPropertyCreate(BaseModel):
    iri: str
    label: str | None = None
    comment: str | None = None
    domain_iri: str | None = None
    range_datatype: XSDDatatype | None = None
    is_functional: bool = False
