"""
api/subgraph.py — 서브그래프 쿼리 라우터

엔드포인트:
  POST /ontologies/{id}/subgraph   서브그래프 쿼리 → Node/Edge 목록
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/ontologies/{ontology_id}",
    tags=["subgraph"],
)


class SubgraphRequest(BaseModel):
    entity_iris: list[str] = Field(..., min_length=1, description="시작점 Entity IRI 목록")
    depth: int = Field(default=2, ge=1, le=5, description="탐색 깊이 (1-5)")


class SubgraphNode(BaseModel):
    iri: str
    label: str
    kind: str  # "concept" | "individual"
    types: list[str] | None = None


class SubgraphEdge(BaseModel):
    source: str   # 소스 노드 IRI
    target: str   # 대상 노드 IRI
    property_iri: str
    property_label: str
    kind: str  # "object" | "data"


class SubgraphResponse(BaseModel):
    nodes: list[SubgraphNode]
    edges: list[SubgraphEdge]


@router.post("/subgraph", response_model=SubgraphResponse)
async def query_subgraph(ontology_id: str, body: SubgraphRequest) -> SubgraphResponse:
    """
    서브그래프 BFS 탐색.

    구현 세부사항:
    - GraphStore.get_subgraph(ontology_id, body.entity_iris, body.depth) 호출
    - Neo4j Cypher:
        MATCH path = (n)-[*1..{depth}]-(m)
        WHERE n.iri IN $iris AND n.ontologyId = $ontologyId
        RETURN nodes(path), relationships(path)
    - 중복 노드 제거 (IRI 기준)
    - 노드 수 최대 500개 제한 (그래프 렌더링 성능 보호)
      초과 시 가장 중심에 가까운 노드 우선 유지
    - Cytoscape.js 호환 형식으로 변환:
      { nodes: [{ iri, label, kind, types }], edges: [{ source, target, propertyIri, ... }] }
    """
    pass
