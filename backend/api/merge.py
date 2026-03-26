"""
api/merge.py — 온톨로지 Merge 라우터

엔드포인트:
  POST /ontologies/{id}/merge/preview   병합 충돌 미리보기
  POST /ontologies/{id}/merge           실제 병합 실행
"""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["merge"])


class ConflictResolution(BaseModel):
    iri: str
    conflict_type: Literal["domain", "range", "label", "superClass"]
    choice: Literal["keep-target", "keep-source", "merge-both"]


class MergePreviewRequest(BaseModel):
    source_ontology_id: str


class MergeRequest(BaseModel):
    source_ontology_id: str
    resolutions: list[ConflictResolution] = []


@router.post("/merge/preview")
async def preview_merge(request: Request, ontology_id: str, body: MergePreviewRequest) -> dict:
    """두 온톨로지 TBox를 비교해 충돌 목록과 자동 병합 가능 항목을 반환."""
    svc = request.app.state.merge_service
    return await svc.detect_conflicts(ontology_id, body.source_ontology_id)


@router.post("/merge")
async def merge_ontologies(request: Request, ontology_id: str, body: MergeRequest) -> dict:
    """두 온톨로지 TBox를 병합."""
    svc = request.app.state.merge_service
    return await svc.merge(ontology_id, body.source_ontology_id, body.resolutions)
