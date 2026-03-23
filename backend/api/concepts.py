"""
api/concepts.py — Concept(owl:Class) CRUD 라우터

엔드포인트:
  GET    /ontologies/{id}/concepts           Concept 목록
  POST   /ontologies/{id}/concepts           Concept 생성
  GET    /ontologies/{id}/concepts/{iri}     Concept 상세
  PUT    /ontologies/{id}/concepts/{iri}     Concept 수정
  DELETE /ontologies/{id}/concepts/{iri}     Concept 삭제
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Annotated

from models.concept import Concept, ConceptCreate, ConceptUpdate
from models.ontology import PaginatedResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}/concepts",
    tags=["concepts"],
)


@router.get("", response_model=PaginatedResponse)
async def list_concepts(
    ontology_id: str,
    q: str | None = Query(None, description="rdfs:label 키워드 필터"),
    super_class: str | None = Query(None, description="rdfs:subClassOf 필터 (IRI)"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse:
    """
    Concept 목록 조회.

    구현 세부사항:
    - TBox Named Graph에서 owl:Class 목록 SPARQL SELECT
    - q 파라미터: FILTER(CONTAINS(LCASE(STR(?label)), LCASE($q))) 조건 추가
    - super_class 파라미터: rdfs:subClassOf <$super_class> 조건 추가
    - 각 클래스의 individualCount를 서브쿼리 COUNT로 집계:
      (SELECT COUNT(?ind) AS ?count WHERE { ?ind a ?cls })
    - LIMIT/OFFSET으로 페이지네이션
    - PaginatedResponse[Concept] 반환
    """
    pass


@router.post("", response_model=Concept, status_code=201)
async def create_concept(ontology_id: str, body: ConceptCreate) -> Concept:
    """
    새 Concept(owl:Class) 생성.

    구현 세부사항:
    - IRI 유효성 검증: 절대 IRI이거나 온톨로지 base IRI 기반 상대 IRI
    - 이미 존재하는 IRI면 HTTPException(409, code="CONCEPT_IRI_DUPLICATE")
    - TBox Named Graph에 SPARQL UPDATE로 트리플 삽입:
        <{body.iri}> a owl:Class ;
          rdfs:label "{body.label}" ;
          rdfs:comment "{body.comment}" .
    - superClasses 목록: <{body.iri}> rdfs:subClassOf <{superIri}> 트리플 삽입
    - restrictions 목록: owl:Restriction blank node 생성
      _:r a owl:Restriction ;
        owl:onProperty <{restriction.propertyIri}> ;
        owl:someValuesFrom <{restriction.value}> .
      <{body.iri}> rdfs:subClassOf _:r .
    - SyncService.trigger_tbox_sync(ontology_id) 비동기 호출
    - 생성된 Concept 반환
    """
    pass


@router.get("/{iri:path}", response_model=Concept)
async def get_concept(ontology_id: str, iri: str) -> Concept:
    """
    Concept 상세 조회.

    구현 세부사항:
    - URL 경로에서 디코딩된 IRI 파라미터 사용 (iri:path로 슬래시 포함)
    - SPARQL SELECT로 해당 IRI의 모든 속성 조회:
        - rdfs:label, rdfs:comment
        - rdfs:subClassOf (superClasses + restrictions 분리)
        - owl:equivalentClass
        - owl:disjointWith
    - owl:Restriction blank node에서 PropertyRestriction 목록 재구성
    - individualCount: SPARQL COUNT(owl:NamedIndividual rdf:type <iri>)
    - 없으면 HTTPException(404, code="CONCEPT_NOT_FOUND")
    """
    pass


@router.put("/{iri:path}", response_model=Concept)
async def update_concept(ontology_id: str, iri: str, body: ConceptUpdate) -> Concept:
    """
    Concept 수정.

    구현 세부사항:
    - 기존 트리플 조회 후 변경 사항만 UPDATE
    - SPARQL DELETE/INSERT 패턴 사용 (atomic UPDATE)
    - label, comment 변경 처리
    - superClasses 변경: 기존 rdfs:subClassOf 삭제 후 새로 삽입
    - restrictions 변경: 기존 owl:Restriction blank node 모두 삭제 후 재생성
    - SyncService.trigger_tbox_sync(ontology_id) 호출
    """
    pass


@router.delete("/{iri:path}", status_code=204)
async def delete_concept(ontology_id: str, iri: str) -> None:
    """
    Concept 삭제.

    구현 세부사항:
    - TBox Named Graph에서 해당 IRI 주어/목적어로 사용된 모든 트리플 삭제
    - rdfs:domain, rdfs:range에서 이 IRI 참조하는 Property 트리플도 정리
    - 소속 Individual에서 rdf:type <iri> 트리플 제거 (Individual 자체는 유지)
    - SyncService.trigger_tbox_sync(ontology_id) 호출
    - 204 No Content 반환
    """
    pass
