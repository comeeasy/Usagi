"""
api/ontologies.py — 온톨로지 CRUD REST 라우터

엔드포인트:
  GET    /ontologies                온톨로지 목록 (페이지네이션)
  POST   /ontologies                새 온톨로지 생성
  GET    /ontologies/{id}           온톨로지 상세 + 통계
  PUT    /ontologies/{id}           메타데이터 수정
  DELETE /ontologies/{id}           온톨로지 삭제
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated

from models.ontology import (
    Ontology,
    OntologyCreate,
    OntologyUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/ontologies", tags=["ontologies"])


@router.get("", response_model=PaginatedResponse)
async def list_ontologies(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse:
    """
    온톨로지 목록 조회.

    구현 세부사항:
    - OntologyStore.list_ontologies(page, page_size) 호출
    - SPARQL: SELECT ?id ?iri ?label ?description ?version ?createdAt ?updatedAt
              WHERE { GRAPH ?g { ?iri a owl:Ontology ; rdfs:label ?label } }
              ORDER BY ?label LIMIT $pageSize OFFSET $(page-1)*pageSize
    - 각 온톨로지에 대해 OntologyStore.get_ontology_stats(id) 병렬 호출
    - PaginatedResponse[Ontology] 반환
    """
    pass


@router.post("", response_model=Ontology, status_code=201)
async def create_ontology(body: OntologyCreate) -> Ontology:
    """
    새 온톨로지 생성.

    구현 세부사항:
    - UUID 생성 → 내부 id
    - body.iri가 이미 존재하면 HTTPException(409, code="ONTOLOGY_IRI_DUPLICATE")
    - TBox Named Graph IRI: f"{body.iri}/tbox"
    - SPARQL UPDATE로 owl:Ontology 트리플 삽입:
        <{body.iri}> a owl:Ontology ;
          rdfs:label "{body.label}" ;
          dc:description "{body.description}" ;
          owl:versionInfo "{body.version}" ;
          dc:created "{now().isoformat()}"^^xsd:dateTime .
    - 생성된 Ontology(id=uuid, stats=빈 통계) 반환
    """
    pass


@router.get("/{ontology_id}", response_model=Ontology)
async def get_ontology(ontology_id: str) -> Ontology:
    """
    온톨로지 상세 조회 + 통계.

    구현 세부사항:
    - OntologyStore에서 ontology_id에 해당하는 메타데이터 SPARQL SELECT
    - 없으면 HTTPException(404, code="ONTOLOGY_NOT_FOUND")
    - stats: SPARQL COUNT로 concepts(owl:Class 수), individuals(owl:NamedIndividual 수),
             objectProperties(owl:ObjectProperty 수), dataProperties(owl:DatatypeProperty 수),
             namedGraphs(Named Graph 수) 조회
    - Ontology 반환
    """
    pass


@router.put("/{ontology_id}", response_model=Ontology)
async def update_ontology(ontology_id: str, body: OntologyUpdate) -> Ontology:
    """
    온톨로지 메타데이터 수정.

    구현 세부사항:
    - 기존 값 조회 후 변경된 필드만 SPARQL DELETE/INSERT UPDATE 실행
    - SPARQL UPDATE 패턴:
        DELETE { GRAPH <tbox> { <iri> rdfs:label ?old } }
        INSERT { GRAPH <tbox> { <iri> rdfs:label "{new}" } }
        WHERE  { GRAPH <tbox> { <iri> rdfs:label ?old } }
    - dc:modified를 현재 시각으로 업데이트
    - 수정된 Ontology 반환
    """
    pass


@router.delete("/{ontology_id}", status_code=204)
async def delete_ontology(ontology_id: str) -> None:
    """
    온톨로지 + 모든 소속 데이터 삭제.

    구현 세부사항:
    - 해당 ontology_id에 속한 모든 Named Graph 목록 조회
      (TBox: <iri>/tbox, ABox: <source_id>/*, inferred: <iri>/inferred)
    - OntologyStore.delete_graph(graph_iri) 반복 호출
    - GraphStore.delete_ontology_data(ontology_id) 호출 → Neo4j 데이터 정리
    - 204 No Content 반환
    """
    pass
