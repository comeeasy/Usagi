"""
온톨로지당 단일 Named Graph IRI: {ontology_iri}/kg

스키마·인스턴스·임포트 데이터는 모두 이 그래프에 저장한다.
TBox/ABox 구분은 UI·쿼리(owl:Class vs owl:NamedIndividual)에서만 한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.ontology_store import OntologyStore


def kg_graph_iri(ontology_iri: str) -> str:
    o = ontology_iri.rstrip("/")
    return f"{o}/kg"


def ontology_iri_from_kg(kg_iri: str) -> str:
    suffix = "/kg"
    if kg_iri.endswith(suffix):
        return kg_iri[: -len(suffix)]
    return kg_iri


async def resolve_kg_graph_iri(
    store: "OntologyStore",
    ontology_uuid: str,
    dataset: str | None = None,
) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 조회 후 kg Named Graph IRI 반환. 없으면 None."""
    esc = ontology_uuid.replace("\\", "\\\\").replace('"', '\\"')
    rows = await store.sparql_select(
        f"""
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX dc:  <http://purl.org/dc/terms/>
        SELECT ?iri WHERE {{
            GRAPH ?g {{ ?iri a owl:Ontology ; dc:identifier "{esc}" }}
        }} LIMIT 1
        """,
        dataset=dataset,
    )
    if not rows:
        return None
    return kg_graph_iri(rows[0]["iri"]["value"])
