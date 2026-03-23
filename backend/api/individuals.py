"""
api/individuals.py — Individual(owl:NamedIndividual) CRUD + Provenance 라우터

엔드포인트:
  GET    /ontologies/{id}/individuals               Individual 목록
  POST   /ontologies/{id}/individuals               Individual 생성 (수동 입력)
  GET    /ontologies/{id}/individuals/{iri}         Individual 상세
  PUT    /ontologies/{id}/individuals/{iri}         Individual 수정
  DELETE /ontologies/{id}/individuals/{iri}         Individual 삭제
  GET    /ontologies/{id}/individuals/{iri}/provenance  Provenance 기록 목록
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Annotated

from models.individual import (
    Individual,
    IndividualCreate,
    IndividualUpdate,
    ProvenanceRecord,
)
from models.ontology import PaginatedResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}/individuals",
    tags=["individuals"],
)


@router.get("", response_model=PaginatedResponse)
async def list_individuals(
    ontology_id: str,
    type_iri: str | None = Query(None, description="rdf:type 필터 (Concept IRI)"),
    concept_iri: str | None = Query(None, description="type_iri 별칭"),
    q: str | None = Query(None, description="rdfs:label 키워드 필터"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse:
    """
    Individual 목록 조회.

    구현 세부사항:
    - SPARQL: SELECT ?iri ?label WHERE { ?iri a owl:NamedIndividual }
    - type_iri/concept_iri: ?iri rdf:type <type_iri> 필터 추가
    - q: rdfs:label CONTAINS 필터
    - 결과: [{ iri, label, types, ontologyId }] + 페이지네이션
    """
    pass


@router.post("", response_model=Individual, status_code=201)
async def create_individual(ontology_id: str, body: IndividualCreate) -> Individual:
    """
    Individual 수동 생성.

    구현 세부사항:
    - IRI 유효성 검증 + 중복 확인
    - Named Graph IRI: f"{ontology_iri}/manual/{uuid4()}"
    - SPARQL UPDATE로 트리플 삽입:
        <{body.iri}> a owl:NamedIndividual ;
          rdfs:label "{body.label}" .
        <{body.iri}> rdf:type <{typeIri}> .  -- 각 type에 대해
        <{body.iri}> <{dpIri}> "{value}"^^<{datatype}> .  -- 각 DataPropertyValue
        <{body.iri}> <{opIri}> <{targetIri}> .  -- 각 ObjectPropertyValue
    - Provenance 트리플 삽입 (prov:generatedAtTime, prov:wasAttributedTo="manual")
    - 생성된 Individual 반환
    """
    pass


@router.get("/{iri:path}", response_model=Individual)
async def get_individual(ontology_id: str, iri: str) -> Individual:
    """
    Individual 상세 조회 (모든 속성값 포함).

    구현 세부사항:
    - 모든 Named Graph를 대상으로 SPARQL SELECT
    - rdf:type 목록 → types
    - DataProperty 트리플 → dataPropertyValues [{propertyIri, value, datatype, graphIri}]
    - ObjectProperty 트리플 → objectPropertyValues [{propertyIri, targetIri, graphIri}]
    - owl:sameAs, owl:differentFrom 목록
    - provenance 기록은 별도 메서드 호출 (또는 인라인 조회)
    """
    pass


@router.put("/{iri:path}", response_model=Individual)
async def update_individual(ontology_id: str, iri: str, body: IndividualUpdate) -> Individual:
    """
    Individual 수정.

    구현 세부사항:
    - conflictPolicy 적용:
      - user-edit-wins: 수동 Named Graph (<iri>/manual/*)에만 기록
        기존 자동수집 값은 보조 Named Graph에 유지 (Provenance 보존)
      - latest-wins: 기존 값의 prov:generatedAtTime과 비교하여 최신 값만 노출
    - 변경된 필드만 SPARQL UPDATE
    """
    pass


@router.delete("/{iri:path}", status_code=204)
async def delete_individual(ontology_id: str, iri: str) -> None:
    """
    Individual 삭제.

    구현 세부사항:
    - 해당 IRI의 모든 Named Graph에서 트리플 삭제
    - Provenance 기록도 함께 삭제
    - Neo4j에서 해당 Individual 노드 삭제 (GraphStore.delete_individual)
    - 204 반환
    """
    pass


@router.get("/{iri:path}/provenance", response_model=list[ProvenanceRecord])
async def get_provenance(ontology_id: str, iri: str) -> list[ProvenanceRecord]:
    """
    Individual Provenance(출처) 기록 조회.

    구현 세부사항:
    - SPARQL: 모든 Named Graph를 순회하며 해당 IRI를 주어로 갖는 그래프 목록 조회
    - 각 Named Graph의 prov:generatedAtTime, prov:wasAttributedTo 값 조회
    - ProvenanceRecord { graphIri, sourceId, sourceType, ingestedAt, tripleCount } 구성
    - tripleCount: SPARQL COUNT(GRAPH <graphIri> { <iri> ?p ?o })
    - 시간 역순(최신 먼저) 정렬
    """
    pass
