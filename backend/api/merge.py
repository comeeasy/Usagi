"""
api/merge.py — 온톨로지 Merge 라우터

엔드포인트:
  POST /ontologies/{id}/merge/preview   병합 충돌 미리보기
  POST /ontologies/{id}/merge           실제 병합 실행
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["merge"])

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def _v(term: dict | None, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


class ConflictResolution(BaseModel):
    iri: str
    conflict_type: Literal["domain", "range", "label", "superClass"]
    choice: Literal["keep-target", "keep-source", "merge-both"]


class MergePreviewRequest(BaseModel):
    source_ontology_id: str


class MergeRequest(BaseModel):
    source_ontology_id: str
    resolutions: list[ConflictResolution] = []


# ── 충돌 미리보기 ─────────────────────────────────────────────────────────

@router.post("/merge/preview")
async def preview_merge(request: Request, ontology_id: str, body: MergePreviewRequest) -> dict:
    """
    두 온톨로지 TBox를 비교해 충돌 목록과 자동 병합 가능 항목을 반환.
    충돌 기준: 동일 IRI의 rdfs:label / rdfs:domain / rdfs:range / rdfs:subClassOf 값 불일치.
    """
    store = request.app.state.ontology_store
    target_tbox = f"{ontology_id}/tbox"
    source_tbox = f"{body.source_ontology_id}/tbox"

    # 소스에 있고 타겟에 있는 IRI 중 label 충돌
    label_rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?targetLabel ?sourceLabel WHERE {{
    GRAPH <{target_tbox}> {{ ?iri rdfs:label ?targetLabel }}
    GRAPH <{source_tbox}> {{ ?iri rdfs:label ?sourceLabel }}
    FILTER(?targetLabel != ?sourceLabel)
}}""")

    domain_rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?targetDomain ?sourceDomain WHERE {{
    GRAPH <{target_tbox}> {{ ?iri rdfs:domain ?targetDomain }}
    GRAPH <{source_tbox}> {{ ?iri rdfs:domain ?sourceDomain }}
    FILTER(?targetDomain != ?sourceDomain)
}}""")

    range_rows = await store.sparql_select(f"""{_P}
SELECT ?iri ?targetRange ?sourceRange WHERE {{
    GRAPH <{target_tbox}> {{ ?iri rdfs:range ?targetRange }}
    GRAPH <{source_tbox}> {{ ?iri rdfs:range ?sourceRange }}
    FILTER(?targetRange != ?sourceRange)
}}""")

    conflicts = []
    for r in label_rows:
        conflicts.append({
            "iri": _v(r.get("iri")),
            "conflict_type": "label",
            "target_value": _v(r.get("targetLabel")),
            "source_value": _v(r.get("sourceLabel")),
        })
    for r in domain_rows:
        conflicts.append({
            "iri": _v(r.get("iri")),
            "conflict_type": "domain",
            "target_value": _v(r.get("targetDomain")),
            "source_value": _v(r.get("sourceDomain")),
        })
    for r in range_rows:
        conflicts.append({
            "iri": _v(r.get("iri")),
            "conflict_type": "range",
            "target_value": _v(r.get("targetRange")),
            "source_value": _v(r.get("sourceRange")),
        })

    # 소스에만 있는 IRI → 자동 병합 가능
    source_only = await store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri WHERE {{
    GRAPH <{source_tbox}> {{ ?iri ?p ?o }}
    FILTER NOT EXISTS {{ GRAPH <{target_tbox}> {{ ?iri ?p2 ?o2 }} }}
}}""")

    return {
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "auto_mergeable_count": len(source_only),
    }


# ── 실제 병합 ─────────────────────────────────────────────────────────────

@router.post("/merge")
async def merge_ontologies(request: Request, ontology_id: str, body: MergeRequest) -> dict:
    """
    두 온톨로지 TBox를 병합.
    1. 소스 TBox의 모든 트리플을 타겟 TBox로 복사 (INSERT ... WHERE)
    2. resolutions에 따라 충돌 해결 (keep-target: 소스 값 무시, keep-source: 타겟 값 교체)
    """
    store = request.app.state.ontology_store
    target_tbox = f"{ontology_id}/tbox"
    source_tbox = f"{body.source_ontology_id}/tbox"

    # 소스 → 타겟 전체 복사 (기존 트리플 보존 + 추가)
    await store.sparql_update(f"""{_P}
INSERT {{
    GRAPH <{target_tbox}> {{ ?s ?p ?o }}
}}
WHERE {{
    GRAPH <{source_tbox}> {{ ?s ?p ?o }}
    FILTER NOT EXISTS {{ GRAPH <{target_tbox}> {{ ?s ?p ?o }} }}
}}""")

    merged_count_rows = await store.sparql_select(f"""{_P}
SELECT (COUNT(*) AS ?cnt) WHERE {{ GRAPH <{target_tbox}> {{ ?s ?p ?o }} }}""")
    merged_count = int(_v(merged_count_rows[0].get("cnt"), "0")) if merged_count_rows else 0

    # 충돌 해결 적용
    for res in body.resolutions:
        if res.choice == "keep-target":
            # 소스에서 가져온 충돌 값 삭제 (이미 타겟 값이 우선)
            pass
        elif res.choice == "keep-source":
            # 타겟의 해당 predicate 값 삭제 후 소스 값은 이미 복사됨
            pred_map = {"label": "rdfs:label", "domain": "rdfs:domain",
                        "range": "rdfs:range", "superClass": "rdfs:subClassOf"}
            pred = pred_map.get(res.conflict_type, "rdfs:label")
            src_val_rows = await store.sparql_select(f"""{_P}
SELECT ?v WHERE {{ GRAPH <{source_tbox}> {{ <{res.iri}> {pred} ?v }} }} LIMIT 1""")
            if src_val_rows:
                src_val = _v(src_val_rows[0].get("v"))
                await store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{target_tbox}> {{ <{res.iri}> {pred} ?o }} }}
WHERE  {{ GRAPH <{target_tbox}> {{ <{res.iri}> {pred} ?o . FILTER(?o != "{src_val}") }} }}""")

    return {
        "merged": True,
        "target_ontology_id": ontology_id,
        "source_ontology_id": body.source_ontology_id,
        "triple_count": merged_count,
    }
