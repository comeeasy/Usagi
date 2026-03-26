"""
services/vector_index.py — fastembed 기반 인메모리 벡터 인덱스

흐름:
  1. OntologyStore SPARQL → (iri, label, kind) 목록
  2. fastembed TextEmbedding → numpy (n, dim) 행렬 (L2 정규화)
  3. 검색: 쿼리 임베딩 @ 행렬 → 코사인 유사도 → top-k

모델: BAAI/bge-small-en-v1.5 (384차원, ~33MB, ONNX)
캐시: TTL 기반 (기본 5분), 명시적 invalidate() 지원
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
_DEFAULT_TTL = 300  # seconds


_SPARQL_PREFIX = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


class VectorIndex:
    """단일 온톨로지에 대한 인메모리 벡터 인덱스."""

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model: Any = None  # fastembed.TextEmbedding — lazy-loaded
        self._embeddings: np.ndarray | None = None  # (n, dim), L2 정규화됨
        self._iris: list[str] = []
        self._labels: list[str] = []
        self._kinds: list[str] = []

    # ── 내부 ──────────────────────────────────────────────────────────────────

    def _get_model(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding  # type: ignore
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    @staticmethod
    def _normalize(mat: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms

    # ── 공개 API ──────────────────────────────────────────────────────────────

    def build(self, items: list[dict]) -> None:
        """
        items: [{"iri": str, "label": str, "kind": str}]

        동기 메서드 — run_in_executor로 호출할 것.
        """
        if not items:
            self._embeddings = None
            self._iris = []
            self._labels = []
            self._kinds = []
            return

        model = self._get_model()
        texts = [it["label"] for it in items]

        raw = np.array(list(model.embed(texts)), dtype=np.float32)
        self._embeddings = self._normalize(raw)
        self._iris = [it["iri"] for it in items]
        self._labels = [it["label"] for it in items]
        self._kinds = [it.get("kind", "concept") for it in items]

        logger.debug("VectorIndex built: %d items, dim=%d", len(items), raw.shape[1])

    def search(self, query: str, k: int = 10) -> list[dict]:
        """
        코사인 유사도 기반 top-k 검색.

        동기 메서드 — run_in_executor로 호출할 것.
        """
        if self._embeddings is None or len(self._iris) == 0:
            return []

        model = self._get_model()
        q_raw = np.array(list(model.embed([query]))[0], dtype=np.float32)
        norm = float(np.linalg.norm(q_raw))
        if norm > 0:
            q_raw = q_raw / norm

        scores: np.ndarray = self._embeddings @ q_raw  # (n,)
        top_n = min(k, len(self._iris))
        indices = np.argsort(scores)[::-1][:top_n]

        return [
            {
                "iri": self._iris[i],
                "label": self._labels[i],
                "kind": self._kinds[i],
                "score": float(scores[i]),
            }
            for i in indices
        ]

    @property
    def size(self) -> int:
        return len(self._iris)


class VectorIndexManager:
    """
    온톨로지별 VectorIndex 관리자.

    - TTL 기반 캐시 (기본 5분)
    - 명시적 invalidate(ontology_iri) 지원
    - 인덱스 빌드는 asyncio executor에서 실행 (이벤트 루프 비블로킹)
    """

    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL,
        ttl_seconds: float = _DEFAULT_TTL,
    ) -> None:
        self._model_name = model_name
        self._ttl = ttl_seconds
        # key: ontology_iri  value: (VectorIndex, built_at_timestamp)
        self._cache: dict[str, tuple[VectorIndex, float]] = {}

    def invalidate(self, ontology_iri: str) -> None:
        """개념/개체 변경 시 해당 온톨로지 인덱스 무효화."""
        self._cache.pop(ontology_iri, None)

    async def search(
        self,
        ontology_iri: str,
        query: str,
        k: int,
        store: Any,
    ) -> list[dict]:
        """벡터 검색. 인덱스가 없거나 TTL 만료 시 자동 재빌드."""
        idx = await self._get_or_build(ontology_iri, store)
        if idx.size == 0:
            return []
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, idx.search, query, k)

    # ── 내부 ──────────────────────────────────────────────────────────────────

    async def _get_or_build(self, ontology_iri: str, store: Any) -> VectorIndex:
        now = time.monotonic()
        cached = self._cache.get(ontology_iri)
        if cached is not None:
            idx, built_at = cached
            if now - built_at < self._ttl:
                return idx

        idx = VectorIndex(self._model_name)
        await self._build(idx, ontology_iri, store)
        self._cache[ontology_iri] = (idx, now)
        return idx

    async def _build(self, idx: VectorIndex, ontology_iri: str, store: Any) -> None:
        tbox_iri = f"{ontology_iri}/tbox"

        rows = await store.sparql_select(f"""{_SPARQL_PREFIX}
SELECT ?iri ?label ?kind WHERE {{
    GRAPH <{tbox_iri}> {{
        {{
            ?iri a owl:Class .
            OPTIONAL {{ ?iri rdfs:label ?label }}
            BIND("concept" AS ?kind)
        }}
        UNION
        {{
            ?iri a owl:NamedIndividual .
            OPTIONAL {{ ?iri rdfs:label ?label }}
            BIND("individual" AS ?kind)
        }}
    }}
}}""")

        items: list[dict] = []
        seen: set[str] = set()
        for r in rows:
            iri = r.get("iri", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)
            raw_label = r.get("label", {}).get("value", "")
            label = raw_label or (iri.split("#")[-1] if "#" in iri else iri.split("/")[-1])
            kind = r.get("kind", {}).get("value", "concept")
            items.append({"iri": iri, "label": label, "kind": kind})

        logger.info("Building vector index for <%s>: %d items", ontology_iri, len(items))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, idx.build, items)
