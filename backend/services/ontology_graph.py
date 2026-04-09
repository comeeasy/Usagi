"""
온톨로지 Named Graph IRI 헬퍼

Graph IRI 규칙:
  - UI 수동 생성:  {ont_iri}/manual
  - 파일 import:   {ont_iri}/imports/{filename}
  - URL import:    {ont_iri}/imports/url/{slug}
  - 표준 import:   {ont_iri}/imports/standard/{name}
  - (레거시 kg):   {ont_iri}/kg  — backward-compat용 유지
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ontology_store import OntologyStore


# ── 기본 IRI 헬퍼 ────────────────────────────────────────────────────────────

def kg_graph_iri(ontology_iri: str) -> str:
    """레거시 단일 KG 그래프 IRI (backward-compat)."""
    o = ontology_iri.rstrip("/")
    return f"{o}/kg"


def ontology_iri_from_kg(kg_iri: str) -> str:
    suffix = "/kg"
    if kg_iri.endswith(suffix):
        return kg_iri[: -len(suffix)]
    return kg_iri


def manual_graph_iri(ontology_iri: str) -> str:
    """UI 수동 생성 데이터용 Named Graph IRI."""
    return f"{ontology_iri.rstrip('/')}/manual"


def import_graph_iri(ontology_iri: str, source_type: str, source_label: str) -> str:
    """
    Import 소스별 Named Graph IRI.

    source_type: "file" | "url" | "standard"
    source_label: 파일명, URL, 표준 이름
    """
    o = ontology_iri.rstrip("/")
    if source_type == "file":
        base = os.path.basename(source_label)
    else:
        base = source_label
    # 안전한 IRI slug: 영문·숫자·점·대시·밑줄만 허용
    slug = re.sub(r"[^\w._-]", "_", base)
    if source_type == "file":
        return f"{o}/imports/{slug}"
    elif source_type == "url":
        return f"{o}/imports/url/{slug}"
    else:  # standard
        return f"{o}/imports/standard/{slug}"


# ── Graph 선택 필터 ───────────────────────────────────────────────────────────

def graphs_filter_clause(graph_iris: list[str], ont_prefix: str) -> str:
    """
    GRAPH ?_g 변수에 대한 SPARQL FILTER 절 반환.

    graph_iris가 있으면 IN 필터,
    없으면 ont_prefix 기반 STRSTARTS 전체 조회.
    """
    if graph_iris:
        iris_str = ", ".join(f"<{iri}>" for iri in graph_iris)
        return f"FILTER(?_g IN ({iris_str}))"
    else:
        o = ont_prefix.rstrip("/")
        return f'FILTER(STRSTARTS(STR(?_g), "{o}/"))'


# ── UUID → IRI 조회 헬퍼 ──────────────────────────────────────────────────────

_RESOLVE_SPARQL = """
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX dc:  <http://purl.org/dc/terms/>
SELECT ?iri WHERE {{
    GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{esc}" }}
}} LIMIT 1
"""


async def resolve_ontology_iri(
    store: "OntologyStore",
    ontology_uuid: str,
    dataset: str | None = None,
) -> str | None:
    """UUID(dc:identifier) → 온톨로지 IRI (suffix 없음). 없으면 None."""
    esc = ontology_uuid.replace("\\", "\\\\").replace('"', '\\"')
    rows = await store.sparql_select(
        _RESOLVE_SPARQL.format(esc=esc),
        dataset=dataset,
    )
    if not rows:
        return None
    return rows[0]["iri"]["value"].rstrip("/")


async def resolve_kg_graph_iri(
    store: "OntologyStore",
    ontology_uuid: str,
    dataset: str | None = None,
) -> str | None:
    """UUID(dc:identifier) → kg Named Graph IRI. 없으면 None. (레거시 backward-compat)"""
    ont_iri = await resolve_ontology_iri(store, ontology_uuid, dataset=dataset)
    if ont_iri is None:
        return None
    return kg_graph_iri(ont_iri)
