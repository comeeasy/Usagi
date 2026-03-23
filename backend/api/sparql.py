"""
api/sparql.py — SPARQL 에디터 엔드포인트 라우터

엔드포인트:
  POST /ontologies/{id}/sparql   SPARQL SELECT / ASK / CONSTRUCT 실행
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(
    prefix="/ontologies/{ontology_id}",
    tags=["sparql"],
)


class SPARQLRequest(BaseModel):
    query: str


class SPARQLResponse(BaseModel):
    variables: list[str]
    bindings: list[dict]
    execution_ms: float | None = None


@router.post("/sparql", response_model=SPARQLResponse)
async def execute_sparql(ontology_id: str, body: SPARQLRequest) -> SPARQLResponse:
    """
    SPARQL 쿼리 실행.

    구현 세부사항:
    - 보안: UPDATE/INSERT/DELETE 키워드 감지 시 HTTPException(403, code="SPARQL_UPDATE_FORBIDDEN")
      - 대소문자 무관 정규식: re.search(r'\\b(INSERT|DELETE|LOAD|CLEAR|CREATE|DROP)\\b', query, re.I)
    - OntologyStore.sparql_select(ontology_id, body.query) 호출
    - 실행 시간 측정: time.perf_counter()
    - SPARQL 문법 오류: HTTPException(400, code="SPARQL_SYNTAX_ERROR", detail=str(err))
    - 결과:
      - SELECT: variables = 바인딩 변수 목록, bindings = 각 행 딕셔너리
      - ASK: variables = [], bindings = [{"result": {"type": "boolean", "value": "true/false"}}]
      - CONSTRUCT: variables = ["s", "p", "o"], bindings = 트리플 목록
    """
    pass
