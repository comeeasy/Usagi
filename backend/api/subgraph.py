"""
api/subgraph.py — Path+Flow Pruning 서브그래프 라우터 (Section 33)

엔드포인트:
  POST /ontologies/{id}/subgraph   서브그래프 쿼리 → Node/Edge 목록

알고리즘: PathRAG (AAAI 2025) 기반 Path-based + Flow Pruning
  1. seed entity 쌍별 BFS 경로 탐색 (선택된 relation type만 허용)
  2. flow score = alpha^(hop_count-1) 계산
  3. min_score 미만 제거 + 상위 max_paths 선택 (pruning)
  4. 선택된 경로의 노드 합집합으로 subgraph 조합
  5. { nodes, edges } 반환

참고: arXiv:2502.14902 "PathRAG: Pruning Graph-based Retrieval Augmented
      Generation with Relational Paths" (AAAI 2025)
"""

from __future__ import annotations

import logging
from itertools import combinations

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from services.ontology_graph import graphs_filter_clause, resolve_ontology_iri
from services.sparql_utils import v as _v

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ontologies/{ontology_id}", tags=["subgraph"])

_MAX_HOPS   = 6    # 경로당 최대 홉 수 (하드캡)
_NODE_LIMIT = 500  # 최대 노드 수
_EDGE_CHUNK = 30   # 엣지 조회 청크 크기

_PREFIXES = """\
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dc:   <http://purl.org/dc/terms/>
"""

# ── 요청 모델 ─────────────────────────────────────────────────────────────────

class SubgraphRequest(BaseModel):
    entity_iris:  list[str] = Field(default=[])
    relation_iris: list[str] = Field(default=[])
    max_paths:    int   = Field(default=50,   ge=1,    le=200)
    alpha:        float = Field(default=0.7,  gt=0.0,  le=1.0)
    min_score:    float = Field(default=0.05, gt=0.0,  le=1.0)


# ── 순수 함수 ─────────────────────────────────────────────────────────────────

def _flow_score(hop_count: int, alpha: float = 0.7) -> float:
    """경로 flow score: 1-hop=1.0, 2-hop=alpha, 3-hop=alpha² ..."""
    return alpha ** max(0, hop_count - 1)


def _prune_paths(
    paths: list[list[str]],
    alpha: float,
    min_score: float,
    max_paths: int,
) -> list[list[str]]:
    """flow score로 정렬 후 min_score 미만 제거, 상위 max_paths 선택."""
    scored = [(path, _flow_score(len(path) - 1, alpha)) for path in paths]
    scored = [(p, s) for p, s in scored if s >= min_score]
    scored.sort(key=lambda x: -x[1])
    return [p for p, _ in scored[:max_paths]]


# ── SPARQL 헬퍼 ───────────────────────────────────────────────────────────────

def _values_clause(iris: set[str] | list[str]) -> str:
    return " ".join(f"<{iri}>" for iri in iris)


def _relation_filter(relations: list[str], var: str = "?p") -> str:
    """relation_iris가 있으면 VALUES 필터 반환, 없으면 빈 문자열."""
    if not relations:
        return ""
    vals = _values_clause(relations)
    return f"VALUES {var} {{ {vals} }}"


async def _get_neighbors(
    store,
    node: str,
    relations: list[str],
    gf: str,
    dataset: str | None,
) -> list[str]:
    """node의 직/역방향 이웃 IRI 목록 조회 (relation 필터 적용)."""
    rel_f = _relation_filter(relations)
    rows = await store.sparql_select(f"""
SELECT DISTINCT ?n WHERE {{
    GRAPH ?_g {{
        {{
            <{node}> ?p ?n .
            FILTER(isIRI(?n))
            {rel_f}
        }}
        UNION
        {{
            ?n ?p ?_orig .
            VALUES ?_orig {{ <{node}> }}
            FILTER(isIRI(?n))
            {rel_f}
        }}
    }}
    {gf}
}} LIMIT {_NODE_LIMIT}
""", dataset=dataset)
    return [_v(r.get("n")) for r in rows if r.get("n")]


async def _bfs_path_find(
    store,
    s: str,
    t: str,
    relations: list[str],
    gf: str,
    max_hops: int,
    dataset: str | None,
) -> list[list[str]]:
    """BFS로 s→t 경로를 탐색한다 (선택된 relation만, 사이클 방지).

    Returns:
        각 경로는 node IRI의 순서 있는 목록 [s, ..., t].
    """
    found: list[list[str]] = []
    # queue: (현재 노드, 지금까지의 경로)
    queue: list[tuple[str, list[str]]] = [(s, [s])]

    while queue:
        node, path = queue.pop(0)
        if len(path) - 1 >= max_hops:
            continue

        neighbors = await _get_neighbors(store, node, relations, gf, dataset)
        for nbr in neighbors:
            if nbr in path:          # 사이클 방지: 현재 경로에 있으면 스킵
                continue
            new_path = path + [nbr]
            if nbr == t:
                found.append(new_path)
            else:
                queue.append((nbr, new_path))

    return found


async def _single_entity_paths(
    store,
    seed: str,
    relations: list[str],
    gf: str,
    dataset: str | None,
) -> list[list[str]]:
    """entity 1개 → 1-hop 이웃을 방사형으로 탐색."""
    neighbors = await _get_neighbors(store, seed, relations, gf, dataset)
    return [[seed, nbr] for nbr in neighbors]


# ── 서브그래프 조합 ────────────────────────────────────────────────────────────

async def _fetch_node_details(
    store,
    node_iris: set[str],
    gf: str,
    ontology_id: str,
    dataset: str | None,
) -> dict[str, dict]:
    """노드 IRI 목록의 label·type을 일괄 조회."""
    if not node_iris:
        return {}
    values = _values_clause(node_iris)
    _CLASS_IRIS = {
        "http://www.w3.org/2002/07/owl#Class",
        "http://www.w3.org/2000/01/rdf-schema#Class",
    }
    rows = await store.sparql_select(f"""
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

    nodes: dict[str, dict] = {}
    for r in rows:
        iri = _v(r.get("n"))
        if not iri or iri in nodes:
            continue
        type_val = _v(r.get("type"))
        kind = "concept" if type_val in _CLASS_IRIS else "individual"
        raw_label = _v(r.get("label"))
        label = raw_label or (iri.split("#")[-1] if "#" in iri else iri.split("/")[-1])
        nodes[iri] = {"iri": iri, "label": label, "kind": kind, "ontologyId": ontology_id}

    # type 쿼리에서 누락된 IRI → individual 기본 처리
    for iri in node_iris:
        if iri not in nodes:
            short = iri.split("#")[-1] if "#" in iri else iri.split("/")[-1]
            nodes[iri] = {"iri": iri, "label": short, "kind": "individual", "ontologyId": ontology_id}

    return nodes


async def _fetch_edges_between(
    store,
    node_set: set[str],
    relations: list[str],
    gf: str,
    dataset: str | None,
) -> list[dict]:
    """node_set 내 노드들 사이의 엣지를 청크로 조회."""
    node_list = list(node_set)
    rel_f = _relation_filter(relations)
    edges: dict[str, dict] = {}

    for i in range(0, len(node_list), _EDGE_CHUNK):
        chunk = node_list[i:i + _EDGE_CHUNK]
        s_values = _values_clause(set(chunk))
        rows = await store.sparql_select(f"""
{_PREFIXES}
SELECT DISTINCT ?s ?p ?o ?pLabel WHERE {{
    GRAPH ?_g {{
        ?s ?p ?o .
        VALUES ?s {{ {s_values} }}
        FILTER(isIRI(?o))
        OPTIONAL {{ ?p rdfs:label ?pLabel }}
        {rel_f}
    }}
    {gf}
}}
""", dataset=dataset)

        for r in rows:
            s = _v(r.get("s"))
            p = _v(r.get("p"))
            o = _v(r.get("o"))
            if not (s and p and o and o in node_set):
                continue
            prop_label = _v(r.get("pLabel")) or (
                p.split("#")[-1] if "#" in p else p.split("/")[-1]
            )
            key = f"{s}|{p}|{o}"
            if key not in edges:
                edges[key] = {
                    "source": s,
                    "target": o,
                    "propertyIri": p,
                    "propertyLabel": prop_label,
                    "kind": "relation",
                }

    return list(edges.values())


# ── 메인 로직 ─────────────────────────────────────────────────────────────────

async def _path_subgraph(
    store,
    ontology_id: str,
    entity_iris: list[str],
    relation_iris: list[str],
    max_paths: int,
    alpha: float,
    min_score: float,
    ont_iri: str,
    dataset: str | None,
    graph_iris: list[str],
) -> dict:
    if not entity_iris:
        return {"nodes": [], "edges": []}

    gf = graphs_filter_clause(graph_iris or [], ont_iri)

    all_paths: list[list[str]] = []

    if len(entity_iris) == 1:
        # 단일 entity → 1-hop 방사형 탐색
        all_paths = await _single_entity_paths(
            store, entity_iris[0], relation_iris, gf, dataset
        )
    else:
        # 다중 entity → 모든 쌍에 대해 BFS 경로 탐색
        for s, t in combinations(entity_iris, 2):
            paths = await _bfs_path_find(
                store, s, t, relation_iris, gf, _MAX_HOPS, dataset
            )
            all_paths.extend(paths)
            # 역방향도 탐색 (t→s)
            reverse_paths = await _bfs_path_find(
                store, t, s, relation_iris, gf, _MAX_HOPS, dataset
            )
            all_paths.extend(reverse_paths)

    if not all_paths:
        # 경로가 없으면 seed entity만 노드로 반환
        seed_nodes = {iri: {
            "iri": iri,
            "label": iri.split("#")[-1] if "#" in iri else iri.split("/")[-1],
            "kind": "individual",
            "ontologyId": ontology_id,
        } for iri in entity_iris}
        return {"nodes": list(seed_nodes.values()), "edges": []}

    # Pruning: flow score 기반 상위 max_paths 선택
    pruned = _prune_paths(all_paths, alpha, min_score, max_paths)

    logger.debug(
        "subgraph: %d raw paths → %d after pruning (alpha=%.2f, min_score=%.3f)",
        len(all_paths), len(pruned), alpha, min_score,
    )

    # 경로에서 노드 합집합 추출
    node_set: set[str] = set()
    for path in pruned:
        node_set.update(path)
    node_set = set(list(node_set)[:_NODE_LIMIT])

    # 노드 상세 조회 + 엣지 조회
    nodes_dict = await _fetch_node_details(store, node_set, gf, ontology_id, dataset)
    edges = await _fetch_edges_between(store, node_set, relation_iris, gf, dataset)

    return {"nodes": list(nodes_dict.values()), "edges": edges}


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.post("/subgraph")
async def get_subgraph(
    request: Request,
    ontology_id: str,
    body: SubgraphRequest,
    dataset: str | None = Query(None),
    graph_iris: list[str] = Query(default=[]),
) -> dict:
    """
    Path+Flow Pruning 서브그래프 탐색.

    선택된 entity 쌍 사이의 경로를 BFS로 탐색하고 flow score로 상위 K개 선택.
    반환: { nodes: [...], edges: [...] }
    """
    store = request.app.state.ontology_store
    ont_iri = await resolve_ontology_iri(store, ontology_id, dataset=dataset)
    if not ont_iri:
        return {"nodes": [], "edges": []}

    return await _path_subgraph(
        store,
        ontology_id,
        body.entity_iris,
        body.relation_iris,
        body.max_paths,
        body.alpha,
        body.min_score,
        ont_iri,
        dataset,
        graph_iris,
    )
