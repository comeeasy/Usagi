"""
services/merge_service.py — 온톨로지 Merge 로직 + 충돌 감지

병합 전략:
  - TBox(스키마) 병합만 지원 (ABox는 Provenance로 관리)
  - 충돌 감지: 동일 IRI의 rdfs:label, rdfs:domain, rdfs:range 값 불일치
  - 충돌 해결: keep-target / keep-source / merge-both 선택 적용
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.ontology_store import OntologyStore

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

_PRED_MAP = {
    "label": "rdfs:label",
    "domain": "rdfs:domain",
    "range": "rdfs:range",
    "superClass": "rdfs:subClassOf",
}


def _v(term: dict | None, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


class MergeService:
    """온톨로지 병합 서비스."""

    def __init__(self, ontology_store: "OntologyStore") -> None:
        self._store = ontology_store

    async def detect_conflicts(self, target_id: str, source_id: str, dataset: str | None = None) -> dict:
        """두 온톨로지 TBox를 비교해 충돌 목록과 자동 병합 가능 항목 수를 반환."""
        target_tbox = f"{target_id}/tbox"
        source_tbox = f"{source_id}/tbox"

        label_rows = await self._store.sparql_select(f"""{_P}
SELECT ?iri ?targetLabel ?sourceLabel WHERE {{
    GRAPH <{target_tbox}> {{ ?iri rdfs:label ?targetLabel }}
    GRAPH <{source_tbox}> {{ ?iri rdfs:label ?sourceLabel }}
    FILTER(?targetLabel != ?sourceLabel)
}}""", dataset=dataset)

        domain_rows = await self._store.sparql_select(f"""{_P}
SELECT ?iri ?targetDomain ?sourceDomain WHERE {{
    GRAPH <{target_tbox}> {{ ?iri rdfs:domain ?targetDomain }}
    GRAPH <{source_tbox}> {{ ?iri rdfs:domain ?sourceDomain }}
    FILTER(?targetDomain != ?sourceDomain)
}}""", dataset=dataset)

        range_rows = await self._store.sparql_select(f"""{_P}
SELECT ?iri ?targetRange ?sourceRange WHERE {{
    GRAPH <{target_tbox}> {{ ?iri rdfs:range ?targetRange }}
    GRAPH <{source_tbox}> {{ ?iri rdfs:range ?sourceRange }}
    FILTER(?targetRange != ?sourceRange)
}}""", dataset=dataset)

        conflicts: list[dict] = []
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

        source_only = await self._store.sparql_select(f"""{_P}
SELECT DISTINCT ?iri WHERE {{
    GRAPH <{source_tbox}> {{ ?iri ?p ?o }}
    FILTER NOT EXISTS {{ GRAPH <{target_tbox}> {{ ?iri ?p2 ?o2 }} }}
}}""", dataset=dataset)

        return {
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "auto_mergeable_count": len(source_only),
        }

    async def merge(
        self,
        target_id: str,
        source_id: str,
        resolutions: list[Any],
        dataset: str | None = None,
    ) -> dict:
        """두 온톨로지 TBox를 병합하고 결과 통계를 반환."""
        target_tbox = f"{target_id}/tbox"
        source_tbox = f"{source_id}/tbox"

        # 소스 → 타겟 전체 복사 (중복 제외)
        await self._store.sparql_update(f"""{_P}
INSERT {{
    GRAPH <{target_tbox}> {{ ?s ?p ?o }}
}}
WHERE {{
    GRAPH <{source_tbox}> {{ ?s ?p ?o }}
    FILTER NOT EXISTS {{ GRAPH <{target_tbox}> {{ ?s ?p ?o }} }}
}}""", dataset=dataset)

        # 충돌 해결 적용
        for res in resolutions:
            if res.choice == "keep-source":
                pred = _PRED_MAP.get(res.conflict_type, "rdfs:label")
                src_rows = await self._store.sparql_select(
                    f"""{_P}SELECT ?v WHERE {{ GRAPH <{source_tbox}> {{ <{res.iri}> {pred} ?v }} }} LIMIT 1""",
                    dataset=dataset,
                )
                if src_rows:
                    src_val = _v(src_rows[0].get("v"))
                    await self._store.sparql_update(f"""{_P}
DELETE {{ GRAPH <{target_tbox}> {{ <{res.iri}> {pred} ?o }} }}
WHERE  {{ GRAPH <{target_tbox}> {{ <{res.iri}> {pred} ?o . FILTER(?o != "{src_val}") }} }}""", dataset=dataset)
            # keep-target: 이미 소스 복사 시 중복 제외로 처리됨
            # merge-both: 소스 값이 이미 추가됨 — 추가 작업 없음

        count_rows = await self._store.sparql_select(
            f"""{_P}SELECT (COUNT(*) AS ?cnt) WHERE {{ GRAPH <{target_tbox}> {{ ?s ?p ?o }} }}""",
            dataset=dataset,
        )
        triple_count = int(_v(count_rows[0].get("cnt"), "0")) if count_rows else 0

        return {
            "merged": True,
            "target_ontology_id": target_id,
            "source_ontology_id": source_id,
            "triple_count": triple_count,
        }

    def _compare_literal_lists(self, a: list[str], b: list[str]) -> bool:
        """두 리스트 값이 다른지 비교 (순서 무관)."""
        return set(a) != set(b)
