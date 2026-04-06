"""
온톨로지 UUID → IRI 스코프용 SPARQL 조각.

개체는 단일 Named Graph `{ontology_iri}/kg`에 저장되므로,
GRAPH ?g 패턴에서는 ?g를 해당 kg 그래프로 제한한다.
"""

from __future__ import annotations

from services.ontology_graph import kg_graph_iri, ontology_iri_from_kg


def ontology_iri_from_tbox(tbox_or_kg: str) -> str:
    """레거시 /tbox 접미사 또는 /kg 접미사에서 온톨로지 베이스 IRI 복원."""
    if tbox_or_kg.endswith("/tbox"):
        return tbox_or_kg[:-5]
    return ontology_iri_from_kg(tbox_or_kg)


def individual_scope_sparql(ontology_iri: str, ontology_uuid: str | None = None) -> str:
    """GRAPH ?g 블록 뒤에 붙여 ?g를 해당 온톨로지 kg 그래프로 제한."""
    del ontology_uuid  # 단일 그래프 모델에서는 미사용
    kg = kg_graph_iri(ontology_iri)
    return f"FILTER( ?g = <{kg}> )"
