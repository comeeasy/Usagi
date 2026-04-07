"""
api/graphs.py — Named Graph 목록 라우터

엔드포인트:
  GET  /ontologies/{id}/graphs   온톨로지에 속한 Named Graph 목록 + 소스 정보
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from api.concepts import _resolve_kg_graph
from services.ontology_graph import kg_graph_iri, resolve_kg_graph_iri

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
    kg = await _resolve_kg_graph(store, ontology_id, dataset=dataset)
    if kg is None:
        raise HTTPException(
            404,
            detail={"code": "ONTOLOGY_NOT_FOUND", "message": f"Ontology not found: {ontology_id}"},
        )

    # 온톨로지 IRI prefix (kg IRI에서 /kg suffix 제거)
    ont_iri_prefix = kg[: -len("/kg")] if kg.endswith("/kg") else kg

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
    iris_filter = " ".join(f"<{iri}>" for iri in graph_iris)
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
