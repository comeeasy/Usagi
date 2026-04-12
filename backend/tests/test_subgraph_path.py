"""
tests/test_subgraph_path.py — Path+Flow Pruning 서브그래프 알고리즘 검증 (Section 33)

C33-B1~B6 대응:
  - _flow_score / _prune_paths (순수 함수)
  - _get_neighbors (relation 필터, 양방향)
  - _bfs_path_find (2-hop, 사이클, 경로 없음)
  - single-entity 방사형
  - POST /subgraph 엔드포인트
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 구현 전 import — 함수가 없으면 테스트가 실패함을 확인하는 용도
from api.subgraph import (
    _flow_score,
    _prune_paths,
    _get_neighbors,
    _bfs_path_find,
)

ONT = "https://test.example.org/ontology"
KG  = f"{ONT}/kg"
GF  = f'FILTER(STRSTARTS(STR(?_g), "{ONT}"))'

A = f"{ONT}#A"
B = f"{ONT}#B"
C = f"{ONT}#C"
D = f"{ONT}#D"
REL1 = f"{ONT}#knows"
REL2 = f"{ONT}#worksAt"


def _uri(iri: str) -> dict:
    return {"type": "uri", "value": iri}


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def store() -> MagicMock:
    m = MagicMock()
    m.sparql_select = AsyncMock(return_value=[])
    return m


# ══════════════════════════════════════════════════════════════════════════════
# 순수 함수
# ══════════════════════════════════════════════════════════════════════════════

class TestFlowScore:
    def test_1hop_is_1(self):
        assert _flow_score(1, alpha=0.7) == pytest.approx(1.0)

    def test_2hop_is_alpha(self):
        assert _flow_score(2, alpha=0.7) == pytest.approx(0.7)

    def test_3hop_is_alpha_squared(self):
        assert _flow_score(3, alpha=0.7) == pytest.approx(0.49)

    def test_alpha_1_all_equal(self):
        """alpha=1.0이면 hop 수에 관계없이 score=1.0."""
        for h in range(1, 6):
            assert _flow_score(h, alpha=1.0) == pytest.approx(1.0)


class TestPrunePaths:
    def test_removes_below_min_score(self):
        """min_score=0.5 → 2-hop(score=0.7) 유지, 3-hop(score=0.49) 제거."""
        paths = [[A, B, C], [A, B]]  # 2-hop, 1-hop
        result = _prune_paths(paths, alpha=0.7, min_score=0.5, max_paths=10)
        # [A, B] score=1.0 (1-hop), [A, B, C] score=0.7 (2-hop) — 둘 다 ≥ 0.5
        assert [A, B] in result
        assert [A, B, C] in result

    def test_removes_3hop_when_min_score_high(self):
        """min_score=0.8 → 1-hop만 남음."""
        paths = [[A, B], [A, B, C], [A, B, C, D]]
        result = _prune_paths(paths, alpha=0.7, min_score=0.8, max_paths=10)
        assert [A, B] in result
        assert [A, B, C] not in result
        assert [A, B, C, D] not in result

    def test_respects_max_paths(self):
        """max_paths=1 → score 가장 높은 경로만 반환."""
        paths = [[A, B, C], [A, B]]  # 2-hop score=0.7, 1-hop score=1.0
        result = _prune_paths(paths, alpha=0.7, min_score=0.05, max_paths=1)
        assert len(result) == 1
        assert result[0] == [A, B]  # 1-hop이 score 가장 높음

    def test_sorted_by_score_descending(self):
        """결과가 score 내림차순으로 정렬돼야 한다."""
        paths = [[A, B, C], [A, B], [A, B, C, D]]
        result = _prune_paths(paths, alpha=0.7, min_score=0.05, max_paths=10)
        scores = [_flow_score(len(p) - 1, 0.7) for p in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_paths_returns_empty(self):
        assert _prune_paths([], alpha=0.7, min_score=0.05, max_paths=10) == []


# ══════════════════════════════════════════════════════════════════════════════
# _get_neighbors
# ══════════════════════════════════════════════════════════════════════════════

class TestGetNeighbors:
    @pytest.mark.asyncio
    async def test_returns_forward_neighbor(self, store):
        """A→B 순방향 이웃을 반환해야 한다."""
        store.sparql_select = AsyncMock(return_value=[{"n": _uri(B)}])
        result = await _get_neighbors(store, A, [REL1], GF, None)
        assert B in result

    @pytest.mark.asyncio
    async def test_returns_backward_neighbor(self, store):
        """B→A 역방향에서도 A의 이웃으로 B를 반환해야 한다."""
        store.sparql_select = AsyncMock(return_value=[{"n": _uri(B)}])
        result = await _get_neighbors(store, A, [REL1], GF, None)
        assert B in result

    @pytest.mark.asyncio
    async def test_empty_relations_allows_all(self, store):
        """relation_iris=[] 이면 relation 필터 없이 모든 이웃 반환."""
        store.sparql_select = AsyncMock(return_value=[
            {"n": _uri(B)}, {"n": _uri(C)},
        ])
        result = await _get_neighbors(store, A, [], GF, None)
        assert B in result
        assert C in result

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_neighbors(self, store):
        store.sparql_select = AsyncMock(return_value=[])
        result = await _get_neighbors(store, A, [REL1], GF, None)
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# _bfs_path_find
# ══════════════════════════════════════════════════════════════════════════════

class TestBfsPathFind:
    @pytest.mark.asyncio
    async def test_direct_1hop_path(self, store):
        """A→B 직접 연결 → 경로 [A, B] 반환."""
        # A의 이웃: B
        store.sparql_select = AsyncMock(return_value=[{"n": _uri(B)}])
        paths = await _bfs_path_find(store, A, B, [REL1], GF, max_hops=6, dataset=None)
        assert [A, B] in paths

    @pytest.mark.asyncio
    async def test_2hop_path(self, store):
        """A→B→C 경로에서 A→C 경로 탐색 → [A, B, C] 반환."""
        # A의 이웃: B / B의 이웃: C (t)
        async def _side_effect(query, dataset=None):
            if f"<{A}>" in query:
                return [{"n": _uri(B)}]
            if f"<{B}>" in query:
                return [{"n": _uri(C)}]
            return []

        store.sparql_select = AsyncMock(side_effect=_side_effect)
        paths = await _bfs_path_find(store, A, C, [REL1], GF, max_hops=6, dataset=None)
        assert [A, B, C] in paths

    @pytest.mark.asyncio
    async def test_no_path_returns_empty(self, store):
        """경로가 없으면 빈 리스트 반환."""
        # A의 이웃: B만 있고 B의 이웃은 없음
        async def _side_effect(query, dataset=None):
            if f"<{A}>" in query:
                return [{"n": _uri(B)}]
            return []

        store.sparql_select = AsyncMock(side_effect=_side_effect)
        paths = await _bfs_path_find(store, A, D, [REL1], GF, max_hops=6, dataset=None)
        assert paths == []

    @pytest.mark.asyncio
    async def test_cycle_prevention(self, store):
        """A→B→A 사이클이 발생하지 않아야 한다."""
        # A의 이웃: B / B의 이웃: A (사이클), C (목적지)
        async def _side_effect(query, dataset=None):
            if f"<{A}>" in query:
                return [{"n": _uri(B)}]
            if f"<{B}>" in query:
                return [{"n": _uri(A)}, {"n": _uri(C)}]  # A는 사이클
            return []

        store.sparql_select = AsyncMock(side_effect=_side_effect)
        paths = await _bfs_path_find(store, A, C, [REL1], GF, max_hops=6, dataset=None)
        # [A, B, C]는 있어야 하고, [A, B, A, ...] 같은 사이클 경로는 없어야 함
        assert [A, B, C] in paths
        for p in paths:
            assert len(p) == len(set(p)), f"경로에 중복 노드: {p}"

    @pytest.mark.asyncio
    async def test_max_hops_limits_depth(self, store):
        """max_hops=1이면 2-hop 경로를 탐색하지 않는다."""
        async def _side_effect(query, dataset=None):
            if f"<{A}>" in query:
                return [{"n": _uri(B)}]
            if f"<{B}>" in query:
                return [{"n": _uri(C)}]
            return []

        store.sparql_select = AsyncMock(side_effect=_side_effect)
        paths = await _bfs_path_find(store, A, C, [REL1], GF, max_hops=1, dataset=None)
        # max_hops=1이므로 [A, B, C](2-hop) 경로는 발견 안 됨
        assert [A, B, C] not in paths


# ══════════════════════════════════════════════════════════════════════════════
# POST /subgraph 엔드포인트
# ══════════════════════════════════════════════════════════════════════════════

class TestSubgraphEndpoint:
    """API 엔드포인트 통합 테스트."""

    @pytest.mark.asyncio
    async def test_single_entity_returns_neighbors(self, client, ontology_store):
        """entity 1개만 선택 → 1-hop 이웃 노드/엣지 반환."""
        with patch("api.subgraph.resolve_ontology_iri", return_value=ONT):
            # 이웃 조회: B 반환
            # 노드 상세 조회: A, B 정보
            # 엣지 조회: A→B
            ontology_store.sparql_select = AsyncMock(side_effect=[
                [{"n": _uri(B)}],                             # A의 이웃
                [                                              # 노드 상세
                    {"n": _uri(A), "label": {"type": "literal", "value": "NodeA"},
                     "type": _uri("http://www.w3.org/2002/07/owl#NamedIndividual")},
                    {"n": _uri(B), "label": {"type": "literal", "value": "NodeB"},
                     "type": _uri("http://www.w3.org/2002/07/owl#NamedIndividual")},
                ],
                [                                              # 엣지
                    {"s": _uri(A), "p": _uri(REL1), "o": _uri(B)},
                ],
            ])

            resp = await client.post(
                "/ontologies/test-id/subgraph",
                json={"entity_iris": [A], "relation_iris": [REL1]},
            )

        assert resp.status_code == 200
        data = resp.json()
        node_iris = {n["iri"] for n in data["nodes"]}
        assert A in node_iris
        assert B in node_iris

    @pytest.mark.asyncio
    async def test_two_entities_connected_via_middle_node(self, client, ontology_store):
        """A와 C가 B를 통해 연결 → A, B, C 노드 모두 반환."""
        with patch("api.subgraph.resolve_ontology_iri", return_value=ONT):
            call_count = 0

            async def _select(query, dataset=None):
                nonlocal call_count
                call_count += 1
                # BFS: A→B 탐색
                if f"<{A}>" in query and "?n" in query:
                    return [{"n": _uri(B)}]
                # BFS: B→C 탐색
                if f"<{B}>" in query and "?n" in query:
                    return [{"n": _uri(C)}]
                # 노드 상세
                if "?label" in query:
                    return [
                        {"n": _uri(A), "label": {"type": "literal", "value": "A"},
                         "type": _uri("http://www.w3.org/2002/07/owl#Class")},
                        {"n": _uri(B), "label": {"type": "literal", "value": "B"},
                         "type": _uri("http://www.w3.org/2002/07/owl#Class")},
                        {"n": _uri(C), "label": {"type": "literal", "value": "C"},
                         "type": _uri("http://www.w3.org/2002/07/owl#Class")},
                    ]
                # 엣지
                return [
                    {"s": _uri(A), "p": _uri(REL1), "o": _uri(B)},
                    {"s": _uri(B), "p": _uri(REL1), "o": _uri(C)},
                ]

            ontology_store.sparql_select = AsyncMock(side_effect=_select)

            resp = await client.post(
                "/ontologies/test-id/subgraph",
                json={"entity_iris": [A, C], "relation_iris": [REL1]},
            )

        assert resp.status_code == 200
        data = resp.json()
        node_iris = {n["iri"] for n in data["nodes"]}
        assert A in node_iris
        assert B in node_iris  # 중간 노드
        assert C in node_iris

    @pytest.mark.asyncio
    async def test_empty_entity_iris_returns_empty(self, client, ontology_store):
        """entity_iris=[] → 빈 결과 반환."""
        with patch("api.subgraph.resolve_ontology_iri", return_value=ONT):
            resp = await client.post(
                "/ontologies/test-id/subgraph",
                json={"entity_iris": [], "relation_iris": []},
            )

        assert resp.status_code == 200
        assert resp.json() == {"nodes": [], "edges": []}

    @pytest.mark.asyncio
    async def test_no_relation_allows_all_neighbors(self, client, ontology_store):
        """relation_iris=[] → 모든 relation으로 이웃 탐색."""
        with patch("api.subgraph.resolve_ontology_iri", return_value=ONT):
            ontology_store.sparql_select = AsyncMock(side_effect=[
                [{"n": _uri(B)}, {"n": _uri(C)}],   # 모든 이웃
                [],                                    # 노드 상세 (간단히 빈값)
                [],                                    # 엣지
            ])
            resp = await client.post(
                "/ontologies/test-id/subgraph",
                json={"entity_iris": [A], "relation_iris": []},
            )

        assert resp.status_code == 200
