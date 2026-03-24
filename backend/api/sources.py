"""
api/sources.py — Backing Source 관리 + 수동 Sync 라우터

엔드포인트:
  GET    /ontologies/{id}/sources                      Backing Source 목록
  POST   /ontologies/{id}/sources                      새 Backing Source 등록
  GET    /ontologies/{id}/sources/{source_id}          Source 상세
  PUT    /ontologies/{id}/sources/{source_id}          Source 설정 수정
  DELETE /ontologies/{id}/sources/{source_id}          Source 삭제
  POST   /ontologies/{id}/sources/{source_id}/sync     수동 즉시 동기화 트리거
"""
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from models.source import BackingSource, BackingSourceCreate, BackingSourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ontologies/{ontology_id}/sources",
    tags=["sources"],
)

# Module-level in-memory store (MVP: persists for process lifetime)
_source_store: dict[str, BackingSource] = {}


@router.get("", response_model=list[BackingSource])
async def list_sources(request: Request, ontology_id: str) -> list[dict]:
    """Backing Source 목록 조회."""
    return [
        s.model_dump()
        for s in _source_store.values()
        if s.ontology_id == ontology_id
    ]


@router.post("", response_model=BackingSource, status_code=201)
async def create_source(
    request: Request,
    ontology_id: str,
    body: BackingSourceCreate,
) -> dict:
    """새 Backing Source 등록."""
    source_id = str(uuid4())
    source = BackingSource(
        id=source_id,
        ontology_id=ontology_id,
        label=body.label,
        source_type=body.source_type,
        concept_iri=body.concept_iri,
        iri_template=body.iri_template,
        property_mappings=body.property_mappings,
        conflict_policy=body.conflict_policy,
        config=body.config,
        status="active",
        last_sync_at=None,
    )
    _source_store[source_id] = source
    logger.info("Created source id=%s for ontology=%s", source_id, ontology_id)
    return source.model_dump()


@router.get("/{source_id}", response_model=BackingSource)
async def get_source(
    request: Request,
    ontology_id: str,
    source_id: str,
) -> dict:
    """Source 상세 조회."""
    source = _source_store.get(source_id)
    if source is None or source.ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return source.model_dump()


@router.put("/{source_id}", response_model=BackingSource)
async def update_source(
    request: Request,
    ontology_id: str,
    source_id: str,
    body: BackingSourceUpdate,
) -> dict:
    """Source 설정 수정."""
    source = _source_store.get(source_id)
    if source is None or source.ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    # Update only fields that are explicitly set in body
    update_data = body.model_dump(exclude_unset=True)
    updated = source.model_copy(update=update_data)
    _source_store[source_id] = updated
    logger.info("Updated source id=%s for ontology=%s", source_id, ontology_id)
    return updated.model_dump()


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    request: Request,
    ontology_id: str,
    source_id: str,
) -> None:
    """Source 삭제. Triple 데이터는 보존(Provenance 이력 유지)."""
    source = _source_store.get(source_id)
    if source is None or source.ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    del _source_store[source_id]
    logger.info("Deleted source id=%s for ontology=%s", source_id, ontology_id)


@router.post("/{source_id}/sync", status_code=202)
async def trigger_sync(
    request: Request,
    ontology_id: str,
    source_id: str,
) -> dict:
    """수동 즉시 동기화 트리거."""
    source = _source_store.get(source_id)
    if source is None or source.ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    job_id = str(uuid4())

    if hasattr(request.app.state, "kafka_producer"):
        try:
            kafka_producer = request.app.state.kafka_producer
            await kafka_producer.publish_sync_command(source_id, "manual")
            logger.info(
                "Published sync command for source=%s, job_id=%s", source_id, job_id
            )
        except Exception as exc:
            logger.error("Failed to publish sync command: %s", exc)

    return {"job_id": job_id, "status": "pending", "source_id": source_id}
