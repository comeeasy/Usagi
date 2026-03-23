"""
api/merge.py — 온톨로지 Merge 라우터

엔드포인트:
  POST /ontologies/{id}/merge/preview   병합 충돌 미리보기
  POST /ontologies/{id}/merge           실제 병합 실행
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

from models.reasoner import JobResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}",
    tags=["merge"],
)


class MergePreviewRequest(BaseModel):
    source_ontology_id: str


class ConflictItem(BaseModel):
    iri: str
    conflict_type: Literal["domain", "range", "label", "superClass"]
    target_value: str | list[str]
    source_value: str | list[str]


class ConflictResolution(BaseModel):
    iri: str
    conflict_type: Literal["domain", "range", "label", "superClass"]
    choice: Literal["keep-target", "keep-source", "merge-both"]


class MergePreviewResponse(BaseModel):
    conflicts: list[ConflictItem]
    auto_mergeable_count: int
    total_source_entities: int


class MergeRequest(BaseModel):
    source_ontology_id: str
    resolutions: list[ConflictResolution]


@router.post("/merge/preview", response_model=MergePreviewResponse)
async def preview_merge(ontology_id: str, body: MergePreviewRequest) -> MergePreviewResponse:
    """
    병합 충돌 미리보기.

    구현 세부사항:
    - MergeService.detect_conflicts(target_id=ontology_id, source_id=body.source_ontology_id) 호출
    - conflicts: 공통 IRI 중 값이 다른 항목 목록
    - auto_mergeable_count: source에만 있는 새 엔티티 (target에 없어 자동 병합 가능)
    - total_source_entities: source TBox의 전체 클래스/속성 수
    """
    pass


@router.post("/merge", response_model=JobResponse, status_code=202)
async def execute_merge(ontology_id: str, body: MergeRequest) -> JobResponse:
    """
    온톨로지 병합 실행.

    구현 세부사항:
    - MergeService.merge(target_id, source_id, body.resolutions) 비동기 실행
    - 충돌 해결 정책 적용:
      - keep-target: source 트리플 스킵
      - keep-source: target 트리플 덮어쓰기
      - merge-both: 두 값 모두 target에 추가 (예: domain 복수)
    - 자동 병합 가능 항목 직접 삽입
    - 완료 후 TBox Named Graph 저장 + SyncService.trigger_tbox_sync() 호출
    - JobResponse(status="pending") 즉시 반환
    """
    pass
