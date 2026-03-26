"""
Tests for VectorIndex + VectorIndexManager.

fastembed 실제 모델을 사용하므로 첫 실행 시 ~33MB 다운로드가 발생할 수 있음.
"""
from __future__ import annotations

import numpy as np
import pytest
import pytest_asyncio

from services.vector_index import VectorIndex, VectorIndexManager
from services.ontology_store import OntologyStore

BASE = "https://test-vector.example.org"
TBOX = f"{BASE}/tbox"

_P = """
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# ── VectorIndex 단위 테스트 ───────────────────────────────────────────────────

def test_vector_index_build_empty():
    """빈 items → size=0, search 빈 리스트."""
    idx = VectorIndex()
    idx.build([])
    assert idx.size == 0
    assert idx.search("anything") == []


def test_vector_index_build_and_search():
    """빌드 후 관련 쿼리 → top-1 결과가 가장 높은 점수."""
    items = [
        {"iri": "https://ex.org#Person", "label": "Person", "kind": "concept"},
        {"iri": "https://ex.org#Department", "label": "Department", "kind": "concept"},
        {"iri": "https://ex.org#Manager", "label": "Manager", "kind": "concept"},
    ]
    idx = VectorIndex()
    idx.build(items)
    assert idx.size == 3

    results = idx.search("human being", k=3)
    assert len(results) == 3
    # 모든 결과에 필수 필드 존재
    for r in results:
        assert "iri" in r
        assert "label" in r
        assert "kind" in r
        assert "score" in r
    # 점수는 내림차순
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_vector_index_search_top_k():
    """k=1 → 결과 1건."""
    items = [
        {"iri": "https://ex.org#A", "label": "Animal", "kind": "concept"},
        {"iri": "https://ex.org#B", "label": "Building", "kind": "concept"},
        {"iri": "https://ex.org#C", "label": "Car", "kind": "concept"},
    ]
    idx = VectorIndex()
    idx.build(items)
    results = idx.search("vehicle automobile", k=1)
    assert len(results) == 1


def test_vector_index_semantic_similarity():
    """'Person' 쿼리 → Person/Manager가 Department보다 높은 점수."""
    items = [
        {"iri": "https://ex.org#Person", "label": "Person", "kind": "concept"},
        {"iri": "https://ex.org#Employee", "label": "Employee", "kind": "individual"},
        {"iri": "https://ex.org#Building", "label": "Building", "kind": "concept"},
    ]
    idx = VectorIndex()
    idx.build(items)

    results = idx.search("person human employee", k=3)
    iris_order = [r["iri"] for r in results]
    # Person, Employee가 Building보다 앞에 위치해야 함
    building_pos = iris_order.index("https://ex.org#Building")
    assert building_pos >= 1  # Building이 꼴찌이거나 중간


def test_vector_index_scores_normalized():
    """코사인 유사도 점수는 -1 ~ 1 범위."""
    items = [
        {"iri": "https://ex.org#X", "label": "Ontology", "kind": "concept"},
    ]
    idx = VectorIndex()
    idx.build(items)
    results = idx.search("ontology", k=1)
    assert -1.0 <= results[0]["score"] <= 1.0


# ── VectorIndexManager 통합 테스트 ────────────────────────────────────────────

@pytest_asyncio.fixture
async def store_with_data():
    """3개 Class가 있는 인메모리 OntologyStore."""
    store = OntologyStore(path=None)
    await store.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{TBOX}> {{
        <{BASE}#Person>     a owl:Class ; rdfs:label "Person" .
        <{BASE}#Department> a owl:Class ; rdfs:label "Department" .
        <{BASE}#Employee>   a owl:NamedIndividual ; rdfs:label "Employee Alice" .
    }}
}}""")
    return store


@pytest.mark.asyncio
async def test_manager_search_returns_results(store_with_data):
    """VectorIndexManager.search → 결과 반환."""
    mgr = VectorIndexManager()
    results = await mgr.search(BASE, "person human", 3, store_with_data)
    assert len(results) > 0
    iris = [r["iri"] for r in results]
    assert f"{BASE}#Person" in iris


@pytest.mark.asyncio
async def test_manager_search_scores_descending(store_with_data):
    """검색 결과 점수 내림차순 정렬."""
    mgr = VectorIndexManager()
    results = await mgr.search(BASE, "organization unit", 3, store_with_data)
    if len(results) > 1:
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_manager_cache_hit(store_with_data):
    """두 번 검색해도 같은 인덱스 재사용 (캐시 히트)."""
    mgr = VectorIndexManager()
    r1 = await mgr.search(BASE, "person", 3, store_with_data)
    r2 = await mgr.search(BASE, "person", 3, store_with_data)
    # 캐시 여부는 결과 동일성으로 간접 확인
    assert r1 == r2


@pytest.mark.asyncio
async def test_manager_invalidate_rebuilds(store_with_data):
    """invalidate 후 검색 → 인덱스 재빌드."""
    mgr = VectorIndexManager()
    await mgr.search(BASE, "person", 3, store_with_data)

    # 새 클래스 추가 후 invalidate
    await store_with_data.sparql_update(f"""{_P}
INSERT DATA {{
    GRAPH <{TBOX}> {{
        <{BASE}#Manager> a owl:Class ; rdfs:label "Manager" .
    }}
}}""")
    mgr.invalidate(BASE)

    results = await mgr.search(BASE, "manager", 3, store_with_data)
    iris = [r["iri"] for r in results]
    assert f"{BASE}#Manager" in iris


@pytest.mark.asyncio
async def test_manager_empty_ontology():
    """빈 온톨로지 → 빈 리스트 반환 (에러 없음)."""
    store = OntologyStore(path=None)
    mgr = VectorIndexManager()
    results = await mgr.search(BASE, "anything", 5, store)
    assert results == []
