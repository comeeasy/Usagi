"""
Reasoner Pydantic models
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ReasonerViolation(BaseModel):
    violation_type: str
    subject_iri: str
    predicate_iri: str | None = None
    object_iri: str | None = None
    message: str
    severity: Literal["error", "warning", "info"] = "error"


class InferredAxiom(BaseModel):
    subject_iri: str
    predicate_iri: str
    object_iri: str
    inference_rule: str
    confidence: float = 1.0


class ReasonerResult(BaseModel):
    ontology_id: str
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    violations: list[ReasonerViolation] = []
    inferred_axioms: list[InferredAxiom] = []
    violation_count: int = 0
    inferred_count: int = 0
    elapsed_seconds: float | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ReasonerJob(BaseModel):
    job_id: str
    ontology_id: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    updated_at: datetime


class ReasonerRunRequest(BaseModel):
    subgraph_iris: list[str] | None = None  # None이면 전체 온톨로지
    include_inferences: bool = True
    check_consistency: bool = True
    reasoner_profile: Literal["EL", "RL", "QL", "FULL"] = "EL"
