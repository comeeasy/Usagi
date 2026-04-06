"""
api/ontologies.py — 온톨로지 CRUD REST 라우터

엔드포인트:
  GET    /ontologies                온톨로지 목록 (페이지네이션)
  POST   /ontologies                새 온톨로지 생성
  GET    /ontologies/{id}           온톨로지 상세 + 통계
  PUT    /ontologies/{id}           메타데이터 수정
  DELETE /ontologies/{id}           온톨로지 삭제
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from models.ontology import (
    Ontology,
    OntologyCreate,
    OntologyStats,
    OntologyUpdate,
    PaginatedResponse,
)
from services.ontology_graph import kg_graph_iri

router = APIRouter(prefix="/ontologies", tags=["ontologies"])


def _v(term: dict | None, default: str = "") -> str:
    """SPARQL 결과 term → str 변환 헬퍼."""
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


# OWL/DC 프리픽스
_PREFIXES = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dc:   <http://purl.org/dc/terms/>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


def _store(request: Request):
    return request.app.state.ontology_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fetch_ontology(store, ontology_id: str, dataset: str | None = None) -> dict:
    """UUID(dc:identifier)로 온톨로지 메타데이터 조회. 없으면 None."""
    rows = await store.sparql_select(f"""
        {_PREFIXES}
        SELECT ?iri ?label ?description ?version ?created ?updated WHERE {{
            GRAPH ?g {{
                ?iri a owl:Ontology ;
                     dc:identifier "{ontology_id}" .
                OPTIONAL {{ ?iri rdfs:label ?label }}
                OPTIONAL {{ ?iri dc:description ?description }}
                OPTIONAL {{ ?iri owl:versionInfo ?version }}
                OPTIONAL {{ ?iri dc:created ?created }}
                OPTIONAL {{ ?iri dc:modified ?updated }}
            }}
        }} LIMIT 1
    """, dataset=dataset)
    return rows[0] if rows else None


# ── 목록 ──────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse)
async def list_ontologies(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    dataset: str | None = Query(None),
) -> dict:
    store = _store(request)
    items_raw, total = await store.list_ontologies(page, page_size, dataset=dataset)

    items = []
    for raw in items_raw:
        iri = raw["iri"]
        ont_id = raw.get("id", "")  # UUID (dc:identifier)
        kg_iri = kg_graph_iri(iri)
        stats_dict = await store.get_ontology_stats(kg_iri, dataset=dataset)
        items.append(Ontology(
            id=ont_id,
            iri=iri,
            label=raw.get("label", iri),
            description=raw.get("description"),
            version=raw.get("version"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            stats=OntologyStats(**stats_dict),
        ))

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ── 생성 ──────────────────────────────────────────────────────────────────

@router.post("", response_model=Ontology, status_code=201)
async def create_ontology(
    request: Request,
    body: OntologyCreate,
    dataset: str | None = Query(None),
) -> Ontology:
    store = _store(request)

    # 중복 IRI 검사
    exists = await store.sparql_ask(f"""
        {_PREFIXES}
        ASK {{ GRAPH ?g {{ <{body.iri}> a owl:Ontology }} }}
    """, dataset=dataset)
    if exists:
        raise HTTPException(409, detail={"code": "ONTOLOGY_IRI_DUPLICATE", "message": f"IRI already exists: {body.iri}"})

    ont_id = str(uuid.uuid4())
    now = _now_iso()
    kg_iri = kg_graph_iri(body.iri)

    desc_triple = f'<{body.iri}> dc:description "{body.description}" .' if body.description else ""
    ver_triple = f'<{body.iri}> owl:versionInfo "{body.version}" .' if body.version else ""

    await store.sparql_update(f"""
        {_PREFIXES}
        INSERT DATA {{
            GRAPH <{kg_iri}> {{
                <{body.iri}> a owl:Ontology ;
                    rdfs:label "{body.label}" ;
                    dc:identifier "{ont_id}" ;
                    dc:created "{now}"^^xsd:dateTime ;
                    dc:modified "{now}"^^xsd:dateTime .
                {desc_triple}
                {ver_triple}
            }}
        }}
    """, dataset=dataset)

    return Ontology(
        id=ont_id,
        iri=body.iri,
        label=body.label,
        description=body.description,
        version=body.version,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
        stats=OntologyStats(),
    )


# ── 상세 조회 ─────────────────────────────────────────────────────────────

@router.get("/{ontology_id}", response_model=Ontology)
async def get_ontology(
    request: Request,
    ontology_id: str,
    dataset: str | None = Query(None),
) -> Ontology:
    store = _store(request)
    raw = await _fetch_ontology(store, ontology_id, dataset=dataset)
    if not raw:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    iri = raw["iri"]["value"]
    kg_iri = kg_graph_iri(iri)
    stats_dict = await store.get_ontology_stats(kg_iri, dataset=dataset)

    return Ontology(
        id=ontology_id,
        iri=iri,
        label=raw.get("label", {}).get("value", iri),
        description=raw.get("description", {}).get("value"),
        version=raw.get("version", {}).get("value"),
        created_at=datetime.fromisoformat(raw["created"]["value"]) if "created" in raw else datetime.now(timezone.utc),
        updated_at=datetime.fromisoformat(raw["updated"]["value"]) if "updated" in raw else datetime.now(timezone.utc),
        stats=OntologyStats(**stats_dict),
    )


# ── 수정 ──────────────────────────────────────────────────────────────────

@router.put("/{ontology_id}", response_model=Ontology)
async def update_ontology(
    request: Request,
    ontology_id: str,
    body: OntologyUpdate,
    dataset: str | None = Query(None),
) -> Ontology:
    store = _store(request)
    raw = await _fetch_ontology(store, ontology_id, dataset=dataset)
    if not raw:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    iri = raw["iri"]["value"]
    kg_iri = kg_graph_iri(iri)
    now = _now_iso()

    # 변경 필드만 UPDATE
    updates = []
    if body.label is not None:
        updates.append(("rdfs:label", body.label, "string"))
    if body.description is not None:
        updates.append(("dc:description", body.description, "string"))
    if body.version is not None:
        updates.append(("owl:versionInfo", body.version, "string"))

    for predicate, value, _ in updates:
        await store.sparql_update(f"""
            {_PREFIXES}
            DELETE {{ GRAPH <{kg_iri}> {{ <{iri}> {predicate} ?old }} }}
            INSERT {{ GRAPH <{kg_iri}> {{ <{iri}> {predicate} "{value}" }} }}
            WHERE  {{ OPTIONAL {{ GRAPH <{kg_iri}> {{ <{iri}> {predicate} ?old }} }} }}
        """, dataset=dataset)

    await store.sparql_update(f"""
        {_PREFIXES}
        DELETE {{ GRAPH <{kg_iri}> {{ <{iri}> dc:modified ?old }} }}
        INSERT {{ GRAPH <{kg_iri}> {{ <{iri}> dc:modified "{now}"^^xsd:dateTime }} }}
        WHERE  {{ OPTIONAL {{ GRAPH <{kg_iri}> {{ <{iri}> dc:modified ?old }} }} }}
    """, dataset=dataset)

    return await get_ontology(request, ontology_id, dataset=dataset)


# ── 삭제 ──────────────────────────────────────────────────────────────────

@router.delete("/{ontology_id}", status_code=204)
async def delete_ontology(
    request: Request,
    ontology_id: str,
    dataset: str | None = Query(None),
) -> None:
    store = _store(request)

    raw = await _fetch_ontology(store, ontology_id, dataset=dataset)
    if not raw:
        raise HTTPException(404, detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"})

    iri = raw["iri"]["value"]

    # 해당 온톨로지 관련 모든 Named Graph 조회 후 삭제
    graph_rows = await store.sparql_select(f"""
        SELECT DISTINCT ?g WHERE {{
            GRAPH ?g {{ ?s ?p ?o }}
            FILTER(STRSTARTS(STR(?g), "{iri}") || STRSTARTS(STR(?g), "urn:source:"))
        }}
    """, dataset=dataset)

    for row in graph_rows:
        await store.delete_graph(_v(row.get("g")), dataset=dataset)
