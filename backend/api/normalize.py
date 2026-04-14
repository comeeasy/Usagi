"""
api/normalize.py — 용어 정규화 + skos:altLabel 관리 라우터

엔드포인트:
  POST   /ontologies/{id}/normalize                단일 용어 정규화
  POST   /ontologies/{id}/normalize/batch          복수 용어 일괄 정규화
  GET    /ontologies/{id}/terms/altlabel           온톨로지 전체 altLabel 목록
  POST   /ontologies/{id}/terms/altlabel           altLabel 등록
  DELETE /ontologies/{id}/terms/altlabel           altLabel 삭제
"""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from services.ontology_graph import resolve_ontology_iri, manual_graph_iri

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["normalize"])


# ── 요청/응답 모델 ────────────────────────────────────────────────────────────

class NormalizeRequest(BaseModel):
    term: str = Field(..., description="정규화할 용어 (은어/약어/비표준어 가능)")
    kind: Literal["concept", "individual", "any"] = Field(
        "any", description="검색 대상 종류"
    )
    threshold: float = Field(
        0.60, ge=0.0, le=1.0,
        description="이 미만이면 requires_review=true"
    )
    dataset: str | None = Field(None, description="Fuseki dataset 이름 (기본값 사용 시 생략)")


class NormalizeResponse(BaseModel):
    term: str
    iri: str | None
    label: str | None
    score: float
    source: str
    candidates: list[dict]
    requires_review: bool


class BatchNormalizeRequest(BaseModel):
    terms: list[str] = Field(..., description="정규화할 용어 목록")
    kind: Literal["concept", "individual", "any"] = "any"
    threshold: float = Field(0.60, ge=0.0, le=1.0)
    dataset: str | None = None


class AltLabelCreate(BaseModel):
    entity_iri: str = Field(..., description="altLabel을 붙일 클래스/개체 IRI")
    label: str = Field(..., description="추가할 altLabel 값")
    lang: str = Field("ko", description="언어 태그 (예: ko, en)")
    dataset: str | None = None


class AltLabelDelete(BaseModel):
    entity_iri: str
    label: str
    lang: str = "ko"
    dataset: str | None = None


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

async def _get_normalizer(request: Request):
    svc = getattr(request.app.state, "term_normalizer", None)
    if svc is None:
        raise HTTPException(503, detail="term_normalizer service not initialized")
    return svc


async def _resolve(request: Request, ontology_id: str, dataset: str | None) -> str:
    store = request.app.state.ontology_store
    iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if iri is None:
        raise HTTPException(404, detail=f"Ontology not found: {ontology_id}")
    return iri


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.post("/normalize", response_model=NormalizeResponse)
async def normalize_term(
    ontology_id: str,
    body: NormalizeRequest,
    request: Request,
):
    """단일 군사 용어를 온톨로지 클래스/개체 IRI로 정규화."""
    normalizer = await _get_normalizer(request)
    result = await normalizer.normalize(
        ontology_id=ontology_id,
        term=body.term,
        kind=body.kind,
        threshold=body.threshold,
        dataset=body.dataset,
    )
    return NormalizeResponse(
        term=body.term,
        iri=result.iri,
        label=result.label,
        score=result.score,
        source=result.source,
        candidates=result.candidates,
        requires_review=result.requires_review,
    )


@router.post("/normalize/batch")
async def normalize_terms_batch(
    ontology_id: str,
    body: BatchNormalizeRequest,
    request: Request,
) -> dict:
    """복수 용어를 일괄 정규화."""
    import asyncio
    normalizer = await _get_normalizer(request)

    async def _one(term: str) -> dict:
        r = await normalizer.normalize(
            ontology_id=ontology_id,
            term=term,
            kind=body.kind,
            threshold=body.threshold,
            dataset=body.dataset,
        )
        return {
            "term": term,
            "iri": r.iri,
            "label": r.label,
            "score": r.score,
            "source": r.source,
            "requires_review": r.requires_review,
            "candidates": r.candidates,
        }

    results = await asyncio.gather(*[_one(t) for t in body.terms])
    review_count = sum(1 for r in results if r["requires_review"])
    return {
        "results": list(results),
        "total": len(results),
        "review_required": review_count,
    }


@router.get("/terms/altlabel")
async def list_alt_labels(
    ontology_id: str,
    request: Request,
    dataset: Annotated[str | None, Query()] = None,
) -> dict:
    """온톨로지 전체의 skos:altLabel 목록 조회."""
    store = request.app.state.ontology_store
    ont_iri = await _resolve(request, ontology_id, dataset)
    items = await store.list_all_alt_labels(ont_iri, dataset=dataset)
    return {"items": items, "total": len(items)}


@router.post("/terms/altlabel", status_code=201)
async def add_alt_label(
    ontology_id: str,
    body: AltLabelCreate,
    request: Request,
) -> dict:
    """entity_iri에 skos:altLabel 추가."""
    store = request.app.state.ontology_store
    ont_iri = await _resolve(request, ontology_id, body.dataset)
    graph_iri = manual_graph_iri(ont_iri)
    await store.add_alt_label(
        graph_iri=graph_iri,
        entity_iri=body.entity_iri,
        label=body.label,
        lang=body.lang,
        dataset=body.dataset,
    )
    # 벡터 인덱스 무효화 (altLabel이 검색에 반영되도록)
    vim = getattr(request.app.state, "vector_index_manager", None)
    if vim is not None:
        vim.invalidate(ont_iri)
    return {
        "status": "created",
        "entity_iri": body.entity_iri,
        "label": body.label,
        "lang": body.lang,
        "graph_iri": graph_iri,
    }


@router.delete("/terms/altlabel")
async def remove_alt_label(
    ontology_id: str,
    body: AltLabelDelete,
    request: Request,
) -> dict:
    """entity_iri에서 skos:altLabel 제거."""
    store = request.app.state.ontology_store
    ont_iri = await _resolve(request, ontology_id, body.dataset)
    graph_iri = manual_graph_iri(ont_iri)
    await store.remove_alt_label(
        graph_iri=graph_iri,
        entity_iri=body.entity_iri,
        label=body.label,
        lang=body.lang,
        dataset=body.dataset,
    )
    vim = getattr(request.app.state, "vector_index_manager", None)
    if vim is not None:
        vim.invalidate(ont_iri)
    return {"status": "deleted", "entity_iri": body.entity_iri, "label": body.label}
