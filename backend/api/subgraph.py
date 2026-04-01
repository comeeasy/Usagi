"""
api/subgraph.py — 서브그래프 쿼리 라우터

엔드포인트:
  POST /ontologies/{id}/subgraph   서브그래프 쿼리 → Node/Edge 목록
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["subgraph"])

_PREFIXES = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX dc:   <http://purl.org/dc/terms/>
"""


async def _resolve_ont_iri(store, ontology_id: str) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 조회."""
    rows = await store.sparql_select(f"""
        {_PREFIXES}
        SELECT ?iri WHERE {{
            GRAPH ?g {{
                ?iri a owl:Ontology ;
                     dc:identifier "{ontology_id}" .
            }}
        }} LIMIT 1
    """)
    if rows:
        term = rows[0].get("iri")
        if isinstance(term, dict):
            return term.get("value")
        return str(term) if term else None
    return None


class SubgraphRequest(BaseModel):
    entity_iris: list[str] = Field(default=[])
    depth: int = Field(default=2, ge=1, le=5)


@router.post("/subgraph")
async def get_subgraph(request: Request, ontology_id: str, body: SubgraphRequest) -> dict:
    """
    Neo4j BFS로 서브그래프 탐색.
    반환: { nodes: [...], edges: [...] }
    """
    graph_store = request.app.state.graph_store
    store = request.app.state.ontology_store
    ont_iri = await _resolve_ont_iri(store, ontology_id)
    return await graph_store.get_subgraph(ontology_id, body.entity_iris, body.depth, ont_iri=ont_iri)
