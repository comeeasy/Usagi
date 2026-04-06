"""
api/merge.py — 온톨로지 Merge 라우터

엔드포인트:
  POST /ontologies/{id}/merge/preview   병합 충돌 미리보기
  POST /ontologies/{id}/merge           실제 병합 실행
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["merge"])


async def _resolve_iri(store, ontology_id: str, dataset: str | None = None) -> str:
    """UUID(dc:identifier)로 온톨로지 IRI 조회. 없으면 HTTPException 404."""
    rows = await store.sparql_select(f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX dc:  <http://purl.org/dc/terms/>
SELECT ?iri WHERE {{
    GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{ontology_id}" }}
}} LIMIT 1""", dataset=dataset)
    if not rows:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    return rows[0]["iri"]["value"]


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
async def preview_merge(
    request: Request,
    ontology_id: str,
    body: MergePreviewRequest,
    dataset: str = Query("ontology"),
) -> dict:
    """두 온톨로지 kg 그래프를 비교해 충돌 목록과 자동 병합 가능 항목을 반환."""
    store = request.app.state.ontology_store
    svc = request.app.state.merge_service
    target_iri = await _resolve_iri(store, ontology_id, dataset=dataset)
    source_iri = await _resolve_iri(store, body.source_ontology_id, dataset=dataset)
    return await svc.detect_conflicts(target_iri, source_iri, dataset=dataset)


@router.post("/merge")
async def merge_ontologies(
    request: Request,
    ontology_id: str,
    body: MergeRequest,
    dataset: str = Query("ontology"),
) -> dict:
    """소스 온톨로지를 타겟 kg 그래프로 병합."""
    store = request.app.state.ontology_store
    svc = request.app.state.merge_service
    target_iri = await _resolve_iri(store, ontology_id, dataset=dataset)
    source_iri = await _resolve_iri(store, body.source_ontology_id, dataset=dataset)
    return await svc.merge(target_iri, source_iri, body.resolutions, dataset=dataset)
