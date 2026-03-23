"""
Ontology Pydantic models
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class OntologyStats(BaseModel):
    class_count: int = 0
    individual_count: int = 0
    property_count: int = 0
    triple_count: int = 0


class Ontology(BaseModel):
    id: str
    name: str
    description: str | None = None
    base_iri: str
    version: str | None = None
    created_at: datetime
    updated_at: datetime
    stats: OntologyStats = Field(default_factory=OntologyStats)


class OntologyCreate(BaseModel):
    name: str
    description: str | None = None
    base_iri: str
    version: str | None = None


class OntologyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    version: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    code: str | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str  # 'pending' | 'running' | 'completed' | 'failed'
    message: str | None = None
    result: dict | None = None
