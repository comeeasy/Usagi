"""
api/properties.py — ObjectProperty / DataProperty CRUD 라우터

엔드포인트:
  GET    /ontologies/{id}/properties           Property 목록
  POST   /ontologies/{id}/properties           Property 생성
  GET    /ontologies/{id}/properties/{iri}     Property 상세
  PUT    /ontologies/{id}/properties/{iri}     Property 수정
  DELETE /ontologies/{id}/properties/{iri}     Property 삭제
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Annotated, Literal

from models.property import ObjectProperty, DataProperty, PropertyCreate, PropertyUpdate
from models.ontology import PaginatedResponse

router = APIRouter(
    prefix="/ontologies/{ontology_id}/properties",
    tags=["properties"],
)


@router.get("", response_model=PaginatedResponse)
async def list_properties(
    ontology_id: str,
    kind: Literal["object", "data"] | None = Query(None, description="object 또는 data"),
    domain: str | None = Query(None, description="rdfs:domain IRI 필터"),
    range_: str | None = Query(None, alias="range", description="rdfs:range IRI 필터"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse:
    """
    Property 목록 조회.

    구현 세부사항:
    - kind="object": owl:ObjectProperty SPARQL SELECT
    - kind="data": owl:DatatypeProperty SPARQL SELECT
    - kind=None: 두 쿼리 실행 후 결과 합산 (UNION)
    - domain 필터: rdfs:domain <$domain> 조건
    - range 필터: rdfs:range <$range> 조건
    - 각 Property의 characteristics(ObjectProperty) 또는 isFunctional(DataProperty) 포함
    - PaginatedResponse[ObjectProperty | DataProperty] 반환
    """
    pass


@router.post("", status_code=201)
async def create_property(ontology_id: str, body: PropertyCreate):
    """
    새 Property 생성.

    구현 세부사항:
    - body.kind="object": owl:ObjectProperty 트리플 삽입
      특성(Transitive, Symmetric 등)은 해당 OWL 클래스로 선언:
      <iri> a owl:TransitiveProperty, owl:ObjectProperty .
    - body.kind="data": owl:DatatypeProperty 트리플 삽입
      body.isFunctional=True이면 a owl:FunctionalProperty 추가
    - rdfs:domain, rdfs:range 트리플 삽입 (복수 허용)
    - SyncService.trigger_tbox_sync(ontology_id) 호출
    """
    pass


@router.get("/{iri:path}")
async def get_property(ontology_id: str, iri: str):
    """
    Property 상세 조회.

    구현 세부사항:
    - SPARQL SELECT로 iri의 rdf:type 확인 (owl:ObjectProperty vs owl:DatatypeProperty)
    - 타입에 따라 ObjectProperty 또는 DataProperty 모델 반환
    - domain, range, superProperties, inverseOf (Object만), characteristics/isFunctional
    """
    pass


@router.put("/{iri:path}")
async def update_property(ontology_id: str, iri: str, body: PropertyUpdate):
    """
    Property 수정.

    구현 세부사항:
    - 변경된 필드만 SPARQL DELETE/INSERT UPDATE
    - characteristics 변경: 기존 OWL 특성 선언 삭제 후 새로 삽입
    - SyncService.trigger_tbox_sync(ontology_id) 호출
    """
    pass


@router.delete("/{iri:path}", status_code=204)
async def delete_property(ontology_id: str, iri: str) -> None:
    """
    Property 삭제.

    구현 세부사항:
    - TBox에서 해당 IRI의 모든 트리플 삭제
    - 해당 Property를 사용한 Individual 값 트리플도 정리 (또는 정책: 값 유지)
    - 204 반환
    """
    pass
