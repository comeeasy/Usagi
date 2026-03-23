"""
Search Service — 검색 (SPARQL + 벡터 검색)
"""
from __future__ import annotations

# TODO: import OntologyStore and result types
# from backend.services.ontology_store import OntologyStore
# from backend.models.concept import Concept
# EntitySearchResult, RelationSearchResult 타입 정의 필요


async def search_entities(
    ontology_id: str,
    q: str,
    kind: str | None = None,
    limit: int = 20,
) -> list:
    """
    SPARQL FILTER(CONTAINS(LCASE(STR(?label)), LCASE(?q))) 로 키워드 검색.
    kind='concept'이면 owl:Class만, 'individual'이면 owl:NamedIndividual만.

    Args:
        ontology_id: 검색 대상 온톨로지 ID
        q: 검색 키워드
        kind: 'concept' | 'individual' | None (전체)
        limit: 최대 반환 수

    Returns:
        list[EntitySearchResult]
    """
    # TODO: implement
    # sparql = _build_entity_sparql(q, kind, limit)
    # store = OntologyStore.get_instance()
    # rows = await store.sparql_select(ontology_id, sparql)
    # return [_row_to_entity(r) for r in rows]
    raise NotImplementedError


async def search_relations(
    ontology_id: str,
    q: str,
    domain_iri: str | None = None,
    range_iri: str | None = None,
    limit: int = 20,
) -> list:
    """
    ObjectProperty + DataProperty SPARQL 검색, domain/range 필터 옵션.

    Args:
        ontology_id: 검색 대상 온톨로지 ID
        q: 검색 키워드
        domain_iri: domain 필터 IRI (옵션)
        range_iri: range 필터 IRI (옵션)
        limit: 최대 반환 수

    Returns:
        list[RelationSearchResult]
    """
    # TODO: implement
    # sparql = _build_relation_sparql(q, domain_iri, range_iri, limit)
    # store = OntologyStore.get_instance()
    # rows = await store.sparql_select(ontology_id, sparql)
    # return [_row_to_relation(r) for r in rows]
    raise NotImplementedError


async def vector_search(
    ontology_id: str,
    text: str,
    k: int = 10,
) -> list:
    """
    텍스트 임베딩 생성 후 pgvector/Qdrant에서 코사인 유사도 검색.
    임베딩 미구축 시 search_entities로 폴백.

    Args:
        ontology_id: 검색 대상 온톨로지 ID
        text: 자연어 검색 텍스트
        k: 반환할 최근접 이웃 수

    Returns:
        list[EntitySearchResult]
    """
    # TODO: implement
    # try:
    #     embedding = await _embed(text)
    #     results = await _cosine_search(ontology_id, embedding, k)
    #     return results
    # except EmbeddingNotBuiltError:
    #     return await search_entities(ontology_id, text, limit=k)
    raise NotImplementedError
