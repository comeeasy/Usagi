"""
api/subgraph.py — 서브그래프 쿼리 라우터

엔드포인트:
  POST /ontologies/{id}/subgraph   서브그래프 쿼리 → Node/Edge 목록

Neo4j Cypher BFS 대신 SPARQL iterative BFS 로 구현한다.
  1. seed IRIs 를 frontier 로 설정
  2. depth 횟수만큼 SPARQL SELECT 로 직/역방향 이웃 IRI 수집
  3. visited IRI 들의 타입/레이블을 일괄 조회
  4. visited IRI 들 사이의 엣지를 청크(30개씩) 조회
  5. { nodes: [...], edges: [...] } 반환
"""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from services.ontology_graph import graphs_filter_clause

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["subgraph"])

_NODE_LIMIT = 500
_EDGE_CHUNK = 30

_PREFIXES = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dc:   <http://purl.org/dc/terms/>
"""


def _v(term, default: str = "") -> str:
    if term is None:
        return default
    if isinstance(term, dict):
        return term.get("value", default)
    return str(term)


async def _resolve_ont_iri(store, ontology_id: str, dataset: str | None = None) -> str | None:
    """UUID(dc:identifier)로 온톨로지 IRI 조회."""
    rows = await store.sparql_select(f"""
        {_PREFIXES}
        SELECT ?iri WHERE {{
            GRAPH ?g {{
                ?iri a owl:Ontology ;
                     dc:identifier "{ontology_id}" .
            }}
        }} LIMIT 1
    """, dataset=dataset)
    return _v(rows[0].get("iri")) if rows else None


def _values_clause(iris: set[str]) -> str:
    return " ".join(f"<{iri}>" for iri in iris)


async def _bfs_expand(
    store,
    frontier: set[str],
    visited: set[str],
    gf: str,
    dataset: str | None = None,
) -> set[str]:
    """frontier 에서 직/역방향 이웃 IRI 를 SPARQL 로 조회하여 반환 (선택된 그래프 내부만)."""
    remaining = _NODE_LIMIT - len(visited)
    if remaining <= 0 or not frontier:
        return set()

    values = _values_clause(frontier)
    rows = await store.sparql_select(f"""
        SELECT DISTINCT ?n WHERE {{
            GRAPH ?_g {{
                {{
                    ?s ?p ?n .
                    VALUES ?s {{ {values} }}
                    FILTER(isIRI(?n))
                }}
                UNION
                {{
                    ?n ?p2 ?o .
                    VALUES ?o {{ {values} }}
                    FILTER(isIRI(?n))
                }}
            }}
            {gf}
        }} LIMIT {remaining}
    """, dataset=dataset)
    return {_v(r.get("n")) for r in rows if r.get("n")} - visited


async def _get_subgraph_sparql(
    store,
    ontology_id: str,
    entity_iris: list[str],
    depth: int,
    ont_iri: str | None,
    dataset: str | None = None,
    graph_iris: list[str] | None = None,
) -> dict:
    depth = max(1, min(depth, 5))

    base_ont_iri = ont_iri or await _resolve_ont_iri(store, ontology_id, dataset=dataset)
    if not base_ont_iri:
        return {"nodes": [], "edges": []}
    gf = graphs_filter_clause(graph_iris or [], base_ont_iri)

    # ── 노드 수집 ──────────────────────────────────────────────────────────
    if entity_iris:
        visited: set[str] = set(entity_iris)
        frontier: set[str] = set(entity_iris)

        for _ in range(depth):
            if not frontier or len(visited) >= _NODE_LIMIT:
                break
            new_iris = await _bfs_expand(store, frontier, visited, gf, dataset=dataset)
            visited |= new_iris
            frontier = new_iris
    else:
        # seed 없음: 선택된 그래프 안의 리소스를 시작점으로 사용
        rows = await store.sparql_select(f"""
            {_PREFIXES}
            SELECT DISTINCT ?n WHERE {{
                GRAPH ?_g {{
                    ?n a ?t .
                }}
                {gf}
            }} LIMIT {_NODE_LIMIT}
        """, dataset=dataset)
        visited = {_v(r.get("n")) for r in rows if r.get("n")}

    visited_list = [iri for iri in visited if iri][:_NODE_LIMIT]

    # ── 노드 상세 조회 (타입·레이블) ──────────────────────────────────────
    nodes: dict[str, dict] = {}
    if visited_list:
        values = _values_clause(set(visited_list))
        detail_rows = await store.sparql_select(f"""
            {_PREFIXES}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?n ?label ?type WHERE {{
                GRAPH ?_g {{
                    ?n a ?type .
                    OPTIONAL {{ ?n rdfs:label ?label }}
                    VALUES ?n {{ {values} }}
                    FILTER(?type IN (owl:Class, rdfs:Class, owl:NamedIndividual))
                }}
                {gf}
            }}
        """, dataset=dataset)
        for r in detail_rows:
            iri = _v(r.get("n"))
            if not iri or iri in nodes:
                continue
            type_val = _v(r.get("type"))
            _CLASS_IRIS = {
                "http://www.w3.org/2002/07/owl#Class",
                "http://www.w3.org/2000/01/rdf-schema#Class",
            }
            kind = "concept" if type_val in _CLASS_IRIS else "individual"
            label = _v(r.get("label")) or iri.split("#")[-1] if "#" in iri else iri.split("/")[-1]
            nodes[iri] = {
                "iri": iri,
                "label": label,
                "kind": kind,
                "ontologyId": ontology_id,
            }

        # 타입 쿼리에서 누락된 IRI 는 individual 로 기본 처리
        for iri in visited_list:
            if iri not in nodes:
                short = iri.split("#")[-1] if "#" in iri else iri.split("/")[-1]
                nodes[iri] = {
                    "iri": iri,
                    "label": short,
                    "kind": "individual",
                    "ontologyId": ontology_id,
                }

    # ── 엣지 수집 ─────────────────────────────────────────────────────────
    visited_set = set(visited_list)
    edges: dict[str, dict] = {}

    for i in range(0, len(visited_list), _EDGE_CHUNK):
        chunk = visited_list[i:i + _EDGE_CHUNK]
        s_values = _values_clause(set(chunk))
        rows = await store.sparql_select(f"""
            {_PREFIXES}
            SELECT DISTINCT ?s ?p ?o ?pLabel WHERE {{
                GRAPH ?_g {{
                    ?s ?p ?o .
                    VALUES ?s {{ {s_values} }}
                    FILTER(isIRI(?o))
                    OPTIONAL {{ ?p rdfs:label ?pLabel }}
                }}
                {gf}
            }}
        """, dataset=dataset)
        for r in rows:
            s = _v(r.get("s"))
            p = _v(r.get("p"))
            o = _v(r.get("o"))
            if not (s and p and o and o in visited_set):
                continue
            prop_label = _v(r.get("pLabel"))
            if not prop_label:
                prop_label = p.split("#")[-1] if "#" in p else p.split("/")[-1]
            key = f"{s}-{p}-{o}"
            if key not in edges:
                edges[key] = {
                    "source": s,
                    "target": o,
                    "propertyIri": p,
                    "propertyLabel": prop_label,
                    "kind": "relation",
                }

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


class SubgraphRequest(BaseModel):
    entity_iris: list[str] = Field(default=[])
    depth: int = Field(default=2, ge=1, le=5)


@router.post("/subgraph")
async def get_subgraph(
    request: Request,
    ontology_id: str,
    body: SubgraphRequest,
    dataset: str | None = Query(None),
    graph_iris: list[str] = Query(default=[]),
) -> dict:
    """
    SPARQL iterative BFS 로 서브그래프 탐색.
    반환: { nodes: [...], edges: [...] }
    """
    store = request.app.state.ontology_store
    ont_iri = await _resolve_ont_iri(store, ontology_id, dataset=dataset)
    return await _get_subgraph_sparql(
        store, ontology_id, body.entity_iris, body.depth, ont_iri,
        dataset=dataset, graph_iris=graph_iris,
    )
