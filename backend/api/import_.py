"""
api/import_.py — 온톨로지 파일/URL Import 라우터

엔드포인트:
  POST /ontologies/{id}/import/file       OWL/TTL/RDF/JSON-LD 파일 업로드
  POST /ontologies/{id}/import/url        URL에서 온톨로지 가져오기
  POST /ontologies/{id}/import/standard   사전 등록 온톨로지 임포트
"""

import logging
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

import services.import_service as import_svc

router = APIRouter(prefix="/ontologies/{ontology_id}/import", tags=["import"])

_EXT_FORMAT = {
    ".ttl": "turtle", ".owl": "xml", ".rdf": "xml",
    ".xml": "xml", ".jsonld": "json-ld", ".json": "json-ld",
    ".nt": "nt", ".n3": "n3",
}


def _fmt_from_filename(name: str) -> str:
    for ext, fmt in _EXT_FORMAT.items():
        if name.lower().endswith(ext):
            return fmt
    return "xml"


async def _resolve_tbox(store, ontology_id: str, dataset: str | None = None) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 조회 후 tbox IRI 반환. 없으면 None."""
    rows = await store.sparql_select(f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX dc:  <http://purl.org/dc/terms/>
        SELECT ?iri WHERE {{
            GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{ontology_id}" }}
        }} LIMIT 1
    """, dataset=dataset)
    if not rows:
        return None
    return f"{rows[0]['iri']['value']}/tbox"


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
    dataset: str = Query("ontology"),
) -> dict:
    """OWL/TTL/RDF/JSON-LD 파일 업로드 후 파싱해 TBox Named Graph에 삽입."""
    store = request.app.state.ontology_store
    tbox_iri = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    content = await file.read()
    fmt = _fmt_from_filename(file.filename or "")

    try:
        triples = await import_svc.parse_file(content, fmt)
    except Exception as e:
        logger.exception("PARSE_ERROR file=%s fmt=%s", file.filename, fmt)
        raise HTTPException(400, detail={"code": "PARSE_ERROR", "message": str(e)})

    count = await import_svc.bulk_insert(store, triples, tbox_iri, dataset=dataset)
    return {"imported": count, "graph_iri": tbox_iri, "format": fmt}


# ── URL 임포트 ────────────────────────────────────────────────────────────

@router.post("/url")
async def import_url(
    request: Request,
    ontology_id: str,
    body: ImportURLRequest,
    dataset: str = Query("ontology"),
) -> dict:
    """URL에서 온톨로지를 다운로드하여 TBox Named Graph에 삽입."""
    store = request.app.state.ontology_store
    tbox_iri = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    try:
        triples = await import_svc.parse_url(body.url)
    except Exception as e:
        raise HTTPException(400, detail={"code": "FETCH_ERROR", "message": str(e)})

    count = await import_svc.bulk_insert(store, triples, tbox_iri, dataset=dataset)
    return {"imported": count, "graph_iri": tbox_iri, "url": body.url}


# ── 표준 온톨로지 ─────────────────────────────────────────────────────────

@router.post("/standard")
async def import_standard(
    request: Request,
    ontology_id: str,
    body: ImportStandardRequest,
    dataset: str = Query("ontology"),
) -> dict:
    """사전 등록된 표준 온톨로지(schema.org, FOAF 등)를 TBox에 삽입."""
    store = request.app.state.ontology_store
    tbox_iri = await _resolve_tbox(store, ontology_id, dataset=dataset)
    if tbox_iri is None:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    try:
        triples = await import_svc.import_standard(body.name)
    except Exception as e:
        raise HTTPException(400, detail={"code": "IMPORT_ERROR", "message": str(e)})

    count = await import_svc.bulk_insert(store, triples, tbox_iri, dataset=dataset)
    return {"imported": count, "graph_iri": tbox_iri, "name": body.name}
