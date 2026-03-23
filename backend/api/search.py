"""
api/search.py — Entity/Relation 검색 라우터

엔드포인트:
  GET  /ontologies/{id}/search/entities    키워드 Entity 검색
  GET  /ontologies/{id}/search/relations   키워드 Property 검색
  POST /ontologies/{id}/search/vector      임베딩 벡터 검색
"""

from fastapi import APIRouter, Query
from typing import Annotated, Literal
from pydantic import BaseModel

router = APIRouter(
    prefix="/ontologies/{ontology_id}/search",
    tags=["search"],
)


class VectorSearchRequest(BaseModel):
    text: str
    k: int = 10


@router.get("/entities")
async def search_entities(
    ontology_id: str,
    q: str = Query(..., min_length=1, description="검색 키워드"),
    kind: Literal["concept", "individual", "all"] = Query("all"),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict]:
    """
    키워드 기반 Entity 검색.

    구현 세부사항:
    - SearchService.keyword_search_entities(ontology_id, q, kind, limit) 호출
    - SPARQL SELECT:
        SELECT ?iri ?label ?type WHERE {
          GRAPH <tbox_iri> { ?iri rdfs:label ?label }
          FILTER(CONTAINS(LCASE(STR(?label)), LCASE($q)))
          OPTIONAL { ?iri rdf:type ?type }
        } LIMIT $limit
    - kind 필터:
        - "concept": FILTER EXISTS { ?iri a owl:Class }
        - "individual": FILTER EXISTS { ?iri a owl:NamedIndividual }
    - matchScore 계산: exact match=1.0, starts_with=0.9, contains=0.8
    - 결과: [{ iri, label, kind, types?, matchScore }]
    """
    pass


@router.get("/relations")
async def search_relations(
    ontology_id: str,
    q: str | None = Query(None),
    domain: str | None = Query(None),
    range_: str | None = Query(None, alias="range"),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict]:
    """
    키워드 기반 Property 검색.

    구현 세부사항:
    - SearchService.keyword_search_relations() 호출
    - q 있으면 rdfs:label CONTAINS 필터
    - domain 있으면 rdfs:domain <$domain> 필터
    - range 있으면 rdfs:range <$range> 필터
    - 결과: [{ iri, label, kind, domain, range, characteristics }]
    """
    pass


@router.post("/vector")
async def vector_search(ontology_id: str, body: VectorSearchRequest) -> list[dict]:
    """
    임베딩 기반 유사 Entity 벡터 검색.

    구현 세부사항:
    - SearchService.vector_search(ontology_id, body.text, body.k) 호출
    - sentence-transformers로 텍스트 임베딩 생성 (all-MiniLM-L6-v2 또는 유사)
    - pgvector: SELECT iri, label, 1-(embedding<=>$vec) AS similarity
               FROM entity_embeddings
               WHERE ontology_id=$ontology_id
               ORDER BY similarity DESC LIMIT k
    - 임베딩 미구축 시 빈 배열 반환 (graceful degradation)
    - 결과: [{ iri, label, kind, similarity }]
    """
    pass
