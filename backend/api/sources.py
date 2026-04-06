"""
api/sources.py — Backing Source 관리 + 수동 Sync 라우터

엔드포인트:
  GET    /ontologies/{id}/sources                        Backing Source 목록
  POST   /ontologies/{id}/sources                        새 Backing Source 등록
  GET    /ontologies/{id}/sources/{source_id}            Source 상세
  PUT    /ontologies/{id}/sources/{source_id}            Source 설정 수정
  DELETE /ontologies/{id}/sources/{source_id}            Source 삭제
  POST   /ontologies/{id}/sources/{source_id}/upload     CSV 파일 업로드 + 즉시 import
  POST   /ontologies/{id}/sources/{source_id}/sync       수동 즉시 동기화 트리거
"""
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile

from models.source import BackingSource, BackingSourceCreate, BackingSourceUpdate, CSVConfig

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ontologies/{ontology_id}/sources",
    tags=["sources"],
)

# Module-level in-memory store (MVP: persists for process lifetime)
_source_store: dict[str, BackingSource] = {}

_UPLOADS_DIR = Path("uploads")
_UPLOADS_DIR.mkdir(exist_ok=True)


# ── CRUD ─────────────────────────────────────────────────────────────────────

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
    # 업로드 파일도 함께 제거
    if source.source_type == "csv-file" and isinstance(source.config, CSVConfig):
        _try_delete_file(source.config.file_name)
    del _source_store[source_id]
    logger.info("Deleted source id=%s for ontology=%s", source_id, ontology_id)


# ── CSV 업로드 + import ───────────────────────────────────────────────────────

@router.post("/{source_id}/upload")
async def upload_csv(
    request: Request,
    ontology_id: str,
    source_id: str,
    file: UploadFile = File(...),
    dataset: str | None = Query(None),
) -> dict:
    """
    CSV 파일 업로드 → Oxigraph + Neo4j 즉시 import.

    응답: { file_name, row_count, headers, triples_inserted, named_graph }
    """
    source = _source_store.get(source_id)
    if source is None or source.ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    if source.source_type != "csv-file":
        raise HTTPException(status_code=400, detail="Source is not of type csv-file")

    # 파일 저장
    safe_name = f"{source_id}_{uuid4().hex[:8]}.csv"
    file_path = _UPLOADS_DIR / safe_name

    content = await file.read()
    file_path.write_bytes(content)
    logger.info("CSV uploaded: %s (%d bytes)", safe_name, len(content))

    # source.config에 파일명 저장
    cfg = source.config if isinstance(source.config, CSVConfig) else CSVConfig()
    updated_cfg = cfg.model_copy(update={"file_name": safe_name})
    _source_store[source_id] = source.model_copy(update={"config": updated_cfg})
    source = _source_store[source_id]

    # import 실행
    store = getattr(request.app.state, "ontology_store", None)

    if store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    from services.ingestion.csv_importer import CSVImporter
    importer = CSVImporter(store)

    try:
        preview = await importer.preview(file_path, source.config)
        result = await importer.import_file(file_path, source, ontology_id, dataset=dataset)
    except Exception as exc:
        logger.error("CSV import failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc

    # last_sync_at 업데이트
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    _source_store[source_id] = _source_store[source_id].model_copy(update={"last_sync_at": now})

    return {
        "file_name": safe_name,
        "headers": preview["headers"],
        "row_count": preview["row_count"],
        **result,
    }


# ── 수동 Sync (csv-file 재import 또는 Kafka 커맨드) ───────────────────────────

@router.post("/{source_id}/sync", status_code=202)
async def trigger_sync(
    request: Request,
    ontology_id: str,
    source_id: str,
    dataset: str | None = Query(None),
) -> dict:
    """
    수동 즉시 동기화 트리거.

    csv-file: 저장된 파일을 재import.
    기타: Kafka sync command 발행.
    """
    source = _source_store.get(source_id)
    if source is None or source.ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    job_id = str(uuid4())

    if source.source_type == "csv-file":
        cfg = source.config if isinstance(source.config, CSVConfig) else CSVConfig()
        if not cfg.file_name:
            raise HTTPException(status_code=400, detail="No CSV file uploaded yet. Use /upload first.")

        file_path = _UPLOADS_DIR / cfg.file_name
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Uploaded file '{cfg.file_name}' not found on server.")

        store = getattr(request.app.state, "ontology_store", None)
        if store is None:
            raise HTTPException(status_code=503, detail="Store not initialized")

        from services.ingestion.csv_importer import CSVImporter
        importer = CSVImporter(store)
        try:
            result = await importer.import_file(file_path, source, ontology_id, dataset=dataset)
        except Exception as exc:
            logger.error("CSV re-import failed: %s", exc)
            raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        _source_store[source_id] = _source_store[source_id].model_copy(update={"last_sync_at": now})

        return {"job_id": job_id, "status": "completed", "source_id": source_id, **result}

    # 기타 소스 유형: Kafka 커맨드
    if hasattr(request.app.state, "kafka_producer"):
        try:
            await request.app.state.kafka_producer.publish_sync_command(source_id, "manual")
        except Exception as exc:
            logger.error("Failed to publish sync command: %s", exc)

    return {"job_id": job_id, "status": "pending", "source_id": source_id}


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────────────

def _try_delete_file(file_name: str) -> None:
    if not file_name:
        return
    try:
        (_UPLOADS_DIR / file_name).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to delete upload file %s: %s", file_name, exc)
