"""
Ontology Pydantic models
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class OntologyStats(BaseModel):
    concepts: int = 0
    individuals: int = 0
    object_properties: int = 0
    data_properties: int = 0
    named_graphs: int = 0


class Ontology(BaseModel):
    id: str
    iri: str
    label: str
    description: str | None = None
    version: str | None = None
    created_at: datetime
    updated_at: datetime
    stats: OntologyStats = Field(default_factory=OntologyStats)


class OntologyCreate(BaseModel):
    iri: str
    label: str
    description: str | None = None
    version: str | None = None


class OntologyUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    version: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool = False


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: object | None = None


class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str   # ISO 8601
    completed_at: str | None = None
    result: object | None = None
    error: str | None = None
