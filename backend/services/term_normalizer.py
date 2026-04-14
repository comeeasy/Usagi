"""
services/term_normalizer.py — 군사 용어 정규화 서비스

임의 문자열(은어·약어·비표준어)을 온톨로지 클래스/개체 IRI로 매핑한다.

매핑 단계 (순서 보장):
  1. 사전 정확 매칭  — backend/data/military_terms.json (variants → canonical)
  2. SPARQL 검색    — rdfs:label + skos:altLabel CONTAINS (대소문자 무시)
  3. 벡터 유사도    — 기존 VectorIndexManager (fastembed BAAI/bge-small-en-v1.5)
  4. (Phase 4) LLM  — Claude API fallback (미구현, 확장 포인트)

반환:
  NormalizeResult
    iri              — 매핑된 클래스/개체 IRI (None = 매핑 실패)
    label            — 매핑된 레이블
    score            — 신뢰도 0.0~1.0
    source           — "dict" | "sparql" | "vector" | "none"
    candidates       — 상위 3개 후보 (검토용)
    requires_review  — score < threshold 시 True
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from services.ontology_graph import resolve_ontology_iri, graphs_filter_clause
from services.sparql_utils import COMMON_PREFIXES, esc as _esc, v as _v

if TYPE_CHECKING:
    from services.ontology_store import OntologyStore
    from services.vector_index import VectorIndexManager

logger = logging.getLogger(__name__)

_DICT_PATH = Path(__file__).parent.parent / "data" / "military_terms.json"
_DEFAULT_THRESHOLD = 0.60


# ── 결과 모델 ────────────────────────────────────────────────────────────────

@dataclass
class NormalizeResult:
    iri: str | None
    label: str | None
    score: float                                    # 0.0 ~ 1.0
    source: Literal["dict", "sparql", "vector", "none"]
    candidates: list[dict] = field(default_factory=list)
    requires_review: bool = False


# ── 사전 로더 ────────────────────────────────────────────────────────────────

def _load_dict() -> dict[str, str]:
    """
    military_terms.json 로드 → {variant_lower: canonical} 역색인.
    canonical 자신도 포함.
    """
    if not _DICT_PATH.exists():
        logger.warning("military_terms.json not found at %s", _DICT_PATH)
        return {}
    with _DICT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    index: dict[str, str] = {}
    for entry in data.get("terms", []):
        canonical: str = entry.get("canonical", "").strip()
        if not canonical:
            continue
        # canonical 자신
        index[canonical.lower()] = canonical
        # 모든 variant
        for var in entry.get("variants", []):
            index[var.strip().lower()] = canonical
    logger.info("Loaded military_terms dict: %d entries", len(index))
    return index


_DICT: dict[str, str] = {}   # 최초 호출 시 lazy 로드


def _get_dict() -> dict[str, str]:
    global _DICT
    if not _DICT:
        _DICT = _load_dict()
    return _DICT


# ── SPARQL 쿼리 ──────────────────────────────────────────────────────────────

_NORMALIZE_SPARQL = """\
{prefixes}
SELECT DISTINCT ?iri ?label ?kind WHERE {{
    GRAPH ?_g {{
        {{
            ?iri a owl:Class .
            BIND("concept" AS ?kind)
        }} UNION {{
            ?iri a owl:NamedIndividual .
            BIND("individual" AS ?kind)
        }}
        OPTIONAL {{ ?iri rdfs:label ?_rdfsLabel }}
        OPTIONAL {{ ?iri skos:altLabel ?_altLabel }}
        BIND(COALESCE(?_rdfsLabel, ?_altLabel) AS ?label)
        FILTER(
            CONTAINS(LCASE(COALESCE(STR(?_rdfsLabel), "")), "{q}") ||
            CONTAINS(LCASE(COALESCE(STR(?_altLabel), "")), "{q}") ||
            CONTAINS(LCASE(STR(?iri)), "{q}")
        )
        FILTER(isIRI(?iri))
    }}
    {gf}
}} ORDER BY ?label LIMIT 10
"""


# ── 메인 서비스 ──────────────────────────────────────────────────────────────

class TermNormalizerService:
    """
    용어 정규화 서비스.

    store, vector_index_manager는 lifespan에서 주입.
    """

    def __init__(
        self,
        store: "OntologyStore",
        vector_index_manager: "VectorIndexManager",
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        self._store = store
        self._vim = vector_index_manager
        self._threshold = threshold

    async def normalize(
        self,
        ontology_id: str,
        term: str,
        kind: Literal["concept", "individual", "any"] = "any",
        threshold: float | None = None,
        dataset: str | None = None,
    ) -> NormalizeResult:
        """
        term을 4단계 체인으로 정규화하여 NormalizeResult 반환.

        ontology_id: UUID 또는 IRI (resolve_ontology_iri로 IRI 변환)
        kind: "concept" | "individual" | "any"
        threshold: 이 미만이면 requires_review = True (기본 _DEFAULT_THRESHOLD)
        """
        thr = threshold if threshold is not None else self._threshold
        term = term.strip()
        if not term:
            return NormalizeResult(
                iri=None, label=None, score=0.0, source="none",
                requires_review=True,
            )

        # 온톨로지 IRI 해석
        ont_iri = await resolve_ontology_iri(self._store, ontology_id, dataset=dataset)
        if ont_iri is None:
            ont_iri = ontology_id.rstrip("/")  # IRI 직접 전달 가능

        # ── Step 1: 사전 정확 매칭 ────────────────────────────────────────
        canonical = _get_dict().get(term.lower())
        if canonical:
            result = await self._sparql_lookup(ont_iri, canonical, kind, dataset)
            if result.iri:
                result.score = 1.0
                result.source = "dict"
                result.requires_review = False
                logger.debug("normalize dict hit: '%s' → '%s'", term, result.iri)
                return result

        # ── Step 2: SPARQL label/altLabel CONTAINS ────────────────────────
        sparql_results = await self._sparql_search(ont_iri, term, kind, dataset)
        if sparql_results:
            best = sparql_results[0]
            score = self._sparql_score(term, best.get("label", ""))
            result = NormalizeResult(
                iri=best["iri"],
                label=best.get("label"),
                score=score,
                source="sparql",
                candidates=sparql_results[:3],
                requires_review=score < thr,
            )
            if score >= thr:
                logger.debug("normalize sparql hit: '%s' → '%s' (%.2f)", term, result.iri, score)
                return result

        # ── Step 3: Vector 유사도 ──────────────────────────────────────────
        vector_results = await self._vim.search(
            ontology_iri=ont_iri,
            query=term,
            k=5,
            store=self._store,
        )
        # kind 필터
        if kind != "any":
            vector_results = [r for r in vector_results if r.get("kind") == kind]

        if vector_results:
            best = vector_results[0]
            score = float(best.get("score", 0.0))
            candidates = [
                {"iri": r["iri"], "label": r.get("label", ""), "kind": r.get("kind", ""), "score": float(r.get("score", 0.0))}
                for r in vector_results[:3]
            ]
            # SPARQL 후보가 있으면 합쳐서 best 재선택
            if sparql_results and sparql_results[0].get("iri"):
                sp_score = self._sparql_score(term, sparql_results[0].get("label", ""))
                if sp_score > score:
                    return NormalizeResult(
                        iri=sparql_results[0]["iri"],
                        label=sparql_results[0].get("label"),
                        score=sp_score,
                        source="sparql",
                        candidates=(sparql_results[:3] + candidates)[:3],
                        requires_review=sp_score < thr,
                    )
            result = NormalizeResult(
                iri=best["iri"],
                label=best.get("label"),
                score=score,
                source="vector",
                candidates=candidates,
                requires_review=score < thr,
            )
            logger.debug("normalize vector hit: '%s' → '%s' (%.2f)", term, result.iri, score)
            return result

        # ── Step 4 자리: LLM fallback (Phase 4에서 구현) ──────────────────
        logger.debug("normalize no match: '%s'", term)
        return NormalizeResult(
            iri=None, label=None, score=0.0, source="none",
            candidates=(sparql_results or [])[:3],
            requires_review=True,
        )

    # ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

    async def _sparql_lookup(
        self,
        ont_iri: str,
        label: str,
        kind: str,
        dataset: str | None,
    ) -> NormalizeResult:
        """정확 레이블로 SPARQL 조회 (사전 canonical 매핑 후 호출)."""
        results = await self._sparql_search(ont_iri, label, kind, dataset)
        if not results:
            return NormalizeResult(iri=None, label=None, score=0.0, source="none")
        best = results[0]
        return NormalizeResult(
            iri=best["iri"],
            label=best.get("label"),
            score=1.0,
            source="sparql",
            candidates=results[:3],
        )

    async def _sparql_search(
        self,
        ont_iri: str,
        term: str,
        kind: str,
        dataset: str | None,
    ) -> list[dict]:
        """SPARQL CONTAINS 검색 → [{"iri", "label", "kind"}] 정렬."""
        gf = graphs_filter_clause([], ont_iri)
        q_escaped = _esc(term.lower())
        q = _NORMALIZE_SPARQL.format(
            prefixes=COMMON_PREFIXES,
            q=q_escaped,
            gf=gf,
        )
        rows = await self._store.sparql_select(q, dataset)

        results = []
        for r in rows:
            iri = _v(r.get("iri"))
            label = _v(r.get("label")) or iri.split("#")[-1] if "#" in (iri or "") else (iri or "").split("/")[-1]
            rk = _v(r.get("kind"), "concept")
            if kind != "any" and rk != kind:
                continue
            results.append({"iri": iri, "label": label, "kind": rk})
        return results

    @staticmethod
    def _sparql_score(term: str, matched_label: str) -> float:
        """
        검색어와 레이블 간 단순 유사도 점수.
        정확 일치 1.0, 포함 관계 0.75, 기타 0.5.
        """
        t = term.lower().strip()
        m = matched_label.lower().strip()
        if not m:
            return 0.4
        if t == m:
            return 1.0
        if t in m or m in t:
            return 0.75
        # 공통 토큰 비율
        t_tokens = set(re.split(r"[\s_\-/]+", t))
        m_tokens = set(re.split(r"[\s_\-/]+", m))
        if t_tokens & m_tokens:
            overlap = len(t_tokens & m_tokens) / max(len(t_tokens), len(m_tokens))
            return 0.5 + 0.25 * overlap
        return 0.4
