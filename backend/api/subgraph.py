"""
api/subgraph.py — 서브그래프 쿼리 라우터

엔드포인트:
  POST /ontologies/{id}/subgraph   서브그래프 쿼리 → Node/Edge 목록
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["subgraph"])


class SubgraphRequest(BaseModel):
    entity_iris: list[str] = Field(..., min_length=1)
    depth: int = Field(default=2, ge=1, le=5)


@router.post("/subgraph")
async def get_subgraph(request: Request, ontology_id: str, body: SubgraphRequest) -> dict:
    """
    Neo4j BFS로 서브그래프 탐색.
    반환: { nodes: [...], edges: [...] }
    """
    graph_store = request.app.state.graph_store
    return await graph_store.get_subgraph(ontology_id, body.entity_iris, body.depth)
