"""
api/graphs.py — Named Graph 목록·TTL 편집 라우터

엔드포인트:
  GET  /ontologies/{id}/graphs              온톨로지에 속한 Named Graph 목록 + 소스 정보
  GET  /ontologies/{id}/graphs/ttl          Named Graph Turtle 조회
  PUT  /ontologies/{id}/graphs/ttl          Named Graph Turtle 교체
"""

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from services.ontology_graph import resolve_ontology_iri

_TURTLE_MEDIA_TYPES = {"text/turtle", "application/x-turtle"}

router = APIRouter(prefix="/ontologies/{ontology_id}/graphs", tags=["graphs"])

# ── 소스 정보 저장용 Named Graph ───────────────────────────────────────────
PROVENANCE_GRAPH = "urn:system:import-provenance"

_SYS = "urn:system:"
PRED_SOURCE_TYPE  = f"{_SYS}importSourceType"
PRED_SOURCE_LABEL = f"{_SYS}importSourceLabel"


class NamedGraph(BaseModel):
    iri: str
    triple_count: int
    source_type: str | None      # "file" | "url" | "standard" | "manual" | None
    source_label: str | None     # 파일명, URL, 표준 온톨로지 이름 등


async def record_import_provenance(
    store,
    graph_iri: str,
    source_type: str,
    source_label: str,
    dataset: str | None = None,
) -> None:
    """import 완료 후 provenance 그래프에 소스 정보를 기록한다."""
    esc_iri = graph_iri.replace("\\", "\\\\").replace('"', '\\"')
    esc_type = source_type.replace("\\", "\\\\").replace('"', '\\"')
    esc_label = source_label.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    await store.sparql_update(
        f"""
        INSERT DATA {{
            GRAPH <{PROVENANCE_GRAPH}> {{
                <{esc_iri}> <{PRED_SOURCE_TYPE}>  "{esc_type}"  .
                <{esc_iri}> <{PRED_SOURCE_LABEL}> "{esc_label}" .
            }}
        }}
        """,
        dataset=dataset,
    )


def _check_graph_ownership(graph_iri: str, ont_iri: str) -> None:
    """graph_iri가 ont_iri 하위에 속하는지 검증. 아니면 403."""
    if not graph_iri.startswith(ont_iri.rstrip("/") + "/"):
        raise HTTPException(
            403,
            detail={
                "code": "GRAPH_NOT_IN_ONTOLOGY",
                "message": f"Graph '{graph_iri}' does not belong to ontology '{ont_iri}'",
            },
        )


# ── TTL 조회 ──────────────────────────────────────────────────────────────────

@router.get("/ttl", response_class=PlainTextResponse)
async def get_graph_ttl(
    request: Request,
    ontology_id: str,
    graph_iri: str = Query(..., description="조회할 Named Graph IRI"),
    dataset: str | None = Query(None),
) -> str:
    """Named Graph 내용을 Turtle 형식으로 반환한다 (GSP GET)."""
    store = request.app.state.ontology_store
    ont_iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if ont_iri is None:
        raise HTTPException(
            404,
            detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"},
        )
    _check_graph_ownership(graph_iri, ont_iri)

    turtle = await store.export_turtle(graph_iri, dataset=dataset)
    return Response(content=turtle, media_type="text/turtle; charset=utf-8")


# ── TTL 교체 ──────────────────────────────────────────────────────────────────

@router.put("/ttl", status_code=204)
async def put_graph_ttl(
    request: Request,
    ontology_id: str,
    graph_iri: str = Query(..., description="교체할 Named Graph IRI"),
    dataset: str | None = Query(None),
) -> None:
    """Named Graph 내용을 Turtle 본문으로 전부 교체한다 (GSP PUT)."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip()
    if content_type not in _TURTLE_MEDIA_TYPES:
        raise HTTPException(
            415,
            detail={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": f"Content-Type must be text/turtle, got '{content_type}'",
            },
        )

    store = request.app.state.ontology_store
    ont_iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if ont_iri is None:
        raise HTTPException(
            404,
            detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"},
        )
    _check_graph_ownership(graph_iri, ont_iri)

    body = await request.body()
    await store.put_graph_turtle(graph_iri, body, dataset=dataset)


@router.get("", response_model=list[NamedGraph])
async def list_graphs(
    request: Request,
    ontology_id: str,
    dataset: str | None = Query(None),
) -> list[dict]:
    """온톨로지에 속한 Named Graph 목록을 반환한다.

    온톨로지 IRI 접두사로 시작하는 그래프만 포함 (kg / inferred 등).
    provenance 그래프에 기록된 소스 정보를 함께 반환한다.
    """
    store = request.app.state.ontology_store
    ont_iri_prefix = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if ont_iri_prefix is None:
        raise HTTPException(
            404,
            detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"},
        )

    # 1. 해당 ontology prefix로 시작하는 Named Graph 목록 + triple count
    rows = await store.sparql_select(
        f"""
        SELECT ?g (COUNT(*) AS ?cnt) WHERE {{
            GRAPH ?g {{ ?s ?p ?o }}
            FILTER(STRSTARTS(STR(?g), "{ont_iri_prefix}"))
        }}
        GROUP BY ?g
        ORDER BY ?g
        """,
        dataset=dataset,
    )

    if not rows:
        return []

    graph_iris = [r["g"]["value"] for r in rows]
    counts = {r["g"]["value"]: int(r["cnt"]["value"]) for r in rows}

    # 2. provenance 그래프에서 소스 정보 일괄 조회
    # SPARQL IN(...) requires comma-separated expressions.
    iris_filter = ", ".join(f"<{iri}>" for iri in graph_iris)
    prov_rows = await store.sparql_select(
        f"""
        SELECT ?g ?type ?label WHERE {{
            GRAPH <{PROVENANCE_GRAPH}> {{
                ?g <{PRED_SOURCE_TYPE}>  ?type  .
                ?g <{PRED_SOURCE_LABEL}> ?label .
                FILTER(?g IN ({iris_filter}))
            }}
        }}
        """,
        dataset=dataset,
    )

    prov: dict[str, dict] = {}
    for r in prov_rows:
        iri = r["g"]["value"]
        prov[iri] = {
            "source_type":  r["type"]["value"],
            "source_label": r["label"]["value"],
        }

    return [
        {
            "iri":          iri,
            "triple_count": counts[iri],
            "source_type":  prov.get(iri, {}).get("source_type"),
            "source_label": prov.get(iri, {}).get("source_label"),
        }
        for iri in graph_iris
    ]
