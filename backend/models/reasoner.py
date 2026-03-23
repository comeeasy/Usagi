"""
Reasoner Pydantic models
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReasonerViolation(BaseModel):
    type: Literal[
        "UnsatisfiableClass",
        "CardinalityViolation",
        "DisjointViolation",
        "DomainRangeViolation",
    ]
    subject_iri: str
    description: str


class InferredAxiom(BaseModel):
    subject: str
    predicate: str
    object: str
    inference_rule: str


class ReasonerResult(BaseModel):
    consistent: bool
    violations: list[ReasonerViolation] = []
    inferred_axioms: list[InferredAxiom] = []
    execution_ms: int


class ReasonerJob(BaseModel):
    job_id: str
    ontology_id: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str       # ISO 8601
    completed_at: str | None = None
    result: ReasonerResult | None = None
    error: str | None = None


class ReasonerRunRequest(BaseModel):
    subgraph_entity_iris: list[str] | None = None  # None이면 전체 온톨로지
