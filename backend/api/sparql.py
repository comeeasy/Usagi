"""
api/sparql.py — SPARQL 에디터 엔드포인트 라우터

엔드포인트:
  POST /ontologies/{id}/sparql   SPARQL SELECT / ASK / CONSTRUCT 실행
"""

import re

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["sparql"])

# UPDATE 키워드 차단 패턴 (보안)
_UPDATE_PATTERN = re.compile(
    r"\b(INSERT\s+DATA|DELETE\s+DATA|INSERT\s+\{|DELETE\s+\{|LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD)\b",
    re.IGNORECASE,
)


class SPARQLRequest(BaseModel):
    query: str


@router.post("/sparql")
async def run_sparql(
    request: Request,
    ontology_id: str,
    body: SPARQLRequest,
    dataset: str | None = Query(None),
) -> dict:
    """
    SPARQL SELECT / ASK 실행.
    UPDATE 구문(INSERT DATA, DELETE DATA 등)은 보안상 차단.
    반환: { variables: [...], bindings: [...] }
    """
    if _UPDATE_PATTERN.search(body.query):
        raise HTTPException(
            400,
            detail={"code": "SPARQL_UPDATE_FORBIDDEN", "message": "SPARQL UPDATE is not allowed via this endpoint"},
        )

    store = request.app.state.ontology_store

    try:
        # ASK 판별
        is_ask = re.search(r"^\s*PREFIX[^A]*\bASK\b|\bASK\b\s*\{", body.query, re.IGNORECASE)

        if is_ask:
            result = await store.sparql_ask(body.query, dataset=dataset)
            return {"variables": ["result"], "bindings": [{"result": {"type": "literal", "value": str(result).lower()}}]}

        rows = await store.sparql_select(body.query, dataset=dataset)
        variables = list(rows[0].keys()) if rows else []
        return {"variables": variables, "bindings": rows}

    except Exception as e:
        err_msg = str(e)
        if "parse" in err_msg.lower() or "syntax" in err_msg.lower():
            raise HTTPException(400, detail={"code": "SPARQL_SYNTAX_ERROR", "message": err_msg})
        raise HTTPException(500, detail={"code": "SPARQL_EXECUTION_ERROR", "message": err_msg})
