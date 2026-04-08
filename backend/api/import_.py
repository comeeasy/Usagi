"""
api/import_.py — 온톨로지 파일/URL Import 라우터

엔드포인트:
  POST /ontologies/{id}/import/file       TTL/RDF/XML/JSON-LD/NT/N3/TriG/N-Quads 등 파일 업로드
  POST /ontologies/{id}/import/url        URL에서 온톨로지 가져오기
  POST /ontologies/{id}/import/standard   사전 등록 온톨로지 임포트
"""

import logging
import time
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

import services.import_service as import_svc
from api.graphs import record_import_provenance
from services.ontology_graph import resolve_ontology_iri, import_graph_iri

router = APIRouter(prefix="/ontologies/{ontology_id}/import", tags=["import"])

_EXT_FORMAT = {
    ".ttl": "turtle",
    ".owl": "xml",
    ".rdf": "xml",
    ".xml": "xml",
    ".jsonld": "json-ld",
    ".json": "json-ld",
    ".nt": "nt",
    ".n3": "n3",
    ".trig": "trig",
    ".nq": "nquads",
}


def _fmt_from_filename(name: str) -> str:
    for ext, fmt in _EXT_FORMAT.items():
        if name.lower().endswith(ext):
            return fmt
    return "xml"


class ImportURLRequest(BaseModel):
    url: str


class ImportStandardRequest(BaseModel):
    name: Literal["schema.org", "foaf", "dc", "skos", "owl", "rdfs"]


# ── 파일 업로드 ───────────────────────────────────────────────────────────

@router.post("/file")
async def import_file(
    request: Request,
    ontology_id: str,
    file: UploadFile = File(...),
    dataset: str | None = Query(None),
) -> dict:
    """OWL/TTL/RDF/JSON-LD 파일 업로드 후 파싱해 파일별 Named Graph에 삽입."""
    store = request.app.state.ontology_store
    ont_iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if ont_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    kg_iri = import_graph_iri(ont_iri, "file", file.filename or "unknown")

    t0 = time.perf_counter()
    content = await file.read()
    ms_read = (time.perf_counter() - t0) * 1000
    logger.info(
        "IMPORT_FILE step=read_body bytes=%d ms=%.1f file=%s ontology_id=%s",
        len(content),
        ms_read,
        file.filename,
        ontology_id,
    )

    fmt = _fmt_from_filename(file.filename or "")

    # Fuseki GSP가 받는 표준 시리얼라이제이션은 원문 POST만 하면 됨(rdflib 파싱→재직렬화 경로 생략).
    gsp_ct = import_svc.gsp_content_type_for_format(fmt)
    if gsp_ct is not None:
        ms_parse = 0.0
        logger.info(
            "IMPORT_FILE step=parse skipped=raw_gsp fmt=%s ct=%s bytes=%d file=%s",
            fmt,
            gsp_ct,
            len(content),
            file.filename,
        )
        t_store = time.perf_counter()
        try:
            count = await import_svc.bulk_insert_raw_gsp(
                store, content, kg_iri, gsp_ct, fmt, dataset=dataset
            )
        except Exception as e:
            logger.exception("RAW_GSP_POST_ERROR file=%s fmt=%s", file.filename, fmt)
            raise HTTPException(400, detail={"code": "IMPORT_ERROR", "message": str(e)})
    else:
        t_parse = time.perf_counter()
        try:
            triples = await import_svc.parse_file(content, fmt)
        except Exception as e:
            logger.exception("PARSE_ERROR file=%s fmt=%s", file.filename, fmt)
            raise HTTPException(400, detail={"code": "PARSE_ERROR", "message": str(e)})
        ms_parse = (time.perf_counter() - t_parse) * 1000
        logger.info(
            "IMPORT_FILE step=parse triples=%d ms=%.1f fmt=%s file=%s",
            len(triples),
            ms_parse,
            fmt,
            file.filename,
        )

        t_store = time.perf_counter()
        count = await import_svc.bulk_insert(store, triples, kg_iri, dataset=dataset)
    ms_store = (time.perf_counter() - t_store) * 1000
    ms_total = (time.perf_counter() - t0) * 1000
    logger.info(
        "IMPORT_FILE step=store triples=%d ms=%.1f graph=%s file=%s",
        count,
        ms_store,
        kg_iri,
        file.filename,
    )
    logger.info(
        "IMPORT_FILE done ontology_id=%s triples=%d format=%s total_ms=%.1f (read=%.1f parse=%.1f store=%.1f) file=%s",
        ontology_id,
        count,
        fmt,
        ms_total,
        ms_read,
        ms_parse,
        ms_store,
        file.filename,
    )
    timing_ms = {
        "read": round(ms_read, 1),
        "parse": round(ms_parse, 1),
        "store": round(ms_store, 1),
        "total": round(ms_total, 1),
    }
    try:
        await record_import_provenance(store, kg_iri, "file", file.filename or "", dataset=dataset)
    except Exception:
        logger.warning("PROVENANCE_WRITE_ERROR graph=%s", kg_iri)

    return {"imported": count, "graph_iri": kg_iri, "format": fmt, "timing_ms": timing_ms}


# ── URL 임포트 ────────────────────────────────────────────────────────────

@router.post("/url")
async def import_url(
    request: Request,
    ontology_id: str,
    body: ImportURLRequest,
    dataset: str | None = Query(None),
) -> dict:
    """URL에서 온톨로지를 다운로드하여 URL별 Named Graph에 삽입."""
    store = request.app.state.ontology_store
    ont_iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if ont_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    kg_iri = import_graph_iri(ont_iri, "url", body.url)

    try:
        triples = await import_svc.parse_url(body.url)
    except Exception as e:
        raise HTTPException(400, detail={"code": "FETCH_ERROR", "message": str(e)})

    count = await import_svc.bulk_insert(store, triples, kg_iri, dataset=dataset)

    try:
        await record_import_provenance(store, kg_iri, "url", body.url, dataset=dataset)
    except Exception:
        logger.warning("PROVENANCE_WRITE_ERROR graph=%s", kg_iri)

    return {"imported": count, "graph_iri": kg_iri, "url": body.url}


# ── 표준 온톨로지 ─────────────────────────────────────────────────────────

@router.post("/standard")
async def import_standard(
    request: Request,
    ontology_id: str,
    body: ImportStandardRequest,
    dataset: str | None = Query(None),
) -> dict:
    """사전 등록된 표준 온톨로지(schema.org, FOAF 등)를 표준별 Named Graph에 삽입."""
    store = request.app.state.ontology_store
    ont_iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if ont_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})
    kg_iri = import_graph_iri(ont_iri, "standard", body.name)

    try:
        triples = await import_svc.import_standard(body.name)
    except Exception as e:
        raise HTTPException(400, detail={"code": "IMPORT_ERROR", "message": str(e)})

    count = await import_svc.bulk_insert(store, triples, kg_iri, dataset=dataset)

    try:
        await record_import_provenance(store, kg_iri, "standard", body.name, dataset=dataset)
    except Exception:
        logger.warning("PROVENANCE_WRITE_ERROR graph=%s", kg_iri)

    return {"imported": count, "graph_iri": kg_iri, "name": body.name}
