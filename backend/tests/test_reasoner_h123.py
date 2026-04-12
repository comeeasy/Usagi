"""
tests/test_reasoner_h123.py — Reasoner H1/H2/H3 개선 검증

H1: entity_iris 필터링 — 지정 엔티티만 violations/inferred 포함
H2: Named Graph 다중 통합 — _get_ont_graphs, _build_combined_rdfxml
H3: SQLite Job Store — create/update/get/list/cleanup
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.reasoner import InferredAxiom, ReasonerResult, ReasonerViolation
from services.job_store import JobStore
from services.reasoner_service import ReasonerService


# ── 공통 fixture ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_jobs.db"


@pytest.fixture
def store_mock() -> MagicMock:
    mock = MagicMock()
    mock.sparql_select = AsyncMock(return_value=[])
    mock.export_turtle = AsyncMock(return_value="")
    return mock


# ══════════════════════════════════════════════════════════════════════════════
# H3: JobStore (SQLite)
# ══════════════════════════════════════════════════════════════════════════════

class TestJobStore:
    """JobStore CRUD 및 TTL 정리 검증."""

    @pytest.mark.asyncio
    async def test_create_then_get_returns_pending(self, tmp_db: Path) -> None:
        """create() 후 get()이 pending 상태를 반환해야 한다."""
        js = JobStore(tmp_db)
        await js.create("job-1", "ont-abc")
        job = await js.get("job-1")
        assert job is not None
        assert job["job_id"] == "job-1"
        assert job["ontology_id"] == "ont-abc"
        assert job["status"] == "pending"

    @pytest.mark.asyncio
    async def test_update_status_to_running(self, tmp_db: Path) -> None:
        """update(status='running') 후 get()이 running을 반환해야 한다."""
        js = JobStore(tmp_db)
        await js.create("job-2", "ont-abc")
        await js.update("job-2", status="running")
        job = await js.get("job-2")
        assert job["status"] == "running"

    @pytest.mark.asyncio
    async def test_update_completed_with_result(self, tmp_db: Path) -> None:
        """update(status='completed', result={...}) 후 get()에 result가 포함돼야 한다."""
        js = JobStore(tmp_db)
        await js.create("job-3", "ont-abc")
        result_data = {"consistent": True, "violations": [], "inferred_axioms": [], "execution_ms": 42}
        await js.update("job-3", status="completed", result=result_data, completed_at="2026-01-01T00:00:00+00:00")
        job = await js.get("job-3")
        assert job["status"] == "completed"
        assert job["result"]["consistent"] is True
        assert job["result"]["execution_ms"] == 42

    @pytest.mark.asyncio
    async def test_get_unknown_returns_none(self, tmp_db: Path) -> None:
        """존재하지 않는 job_id → None 반환."""
        js = JobStore(tmp_db)
        assert await js.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_list_by_ontology(self, tmp_db: Path) -> None:
        """list_by_ontology()가 해당 ontology_id의 job만 반환해야 한다."""
        js = JobStore(tmp_db)
        await js.create("job-A", "ont-1")
        await js.create("job-B", "ont-1")
        await js.create("job-C", "ont-2")
        jobs = await js.list_by_ontology("ont-1")
        ids = {j["job_id"] for j in jobs}
        assert ids == {"job-A", "job-B"}

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_old_jobs(self, tmp_db: Path) -> None:
        """7일 초과 completed job은 cleanup_expired()로 삭제돼야 한다."""
        from datetime import datetime, timedelta, timezone

        js = JobStore(tmp_db)
        await js.create("job-old", "ont-x")
        # DB에 직접 오래된 created_at 세팅
        import sqlite3
        old_date = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        conn = sqlite3.connect(str(tmp_db))
        conn.execute("UPDATE jobs SET status='completed', created_at=? WHERE job_id='job-old'", (old_date,))
        conn.commit()
        conn.close()

        deleted = await js.cleanup_expired()
        assert deleted == 1
        assert await js.get("job-old") is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_keeps_recent_jobs(self, tmp_db: Path) -> None:
        """최근 completed job은 cleanup_expired()로 삭제되지 않아야 한다."""
        js = JobStore(tmp_db)
        await js.create("job-new", "ont-x")
        await js.update("job-new", status="completed", completed_at="2099-01-01T00:00:00+00:00")
        deleted = await js.cleanup_expired()
        assert deleted == 0
        assert await js.get("job-new") is not None


# ══════════════════════════════════════════════════════════════════════════════
# H1: entity_iris 필터링
# ══════════════════════════════════════════════════════════════════════════════

ONT_IRI = "https://test.example.org/ontology"
E1 = f"{ONT_IRI}/entity/A"
E2 = f"{ONT_IRI}/entity/B"
E3 = f"{ONT_IRI}/entity/C"

def _make_result(violations=None, inferred=None) -> ReasonerResult:
    return ReasonerResult(
        consistent=True,
        violations=violations or [],
        inferred_axioms=inferred or [],
        execution_ms=10,
    )


class TestFilterByEntities:
    """_filter_by_entities 단위 검증."""

    def test_filters_violations_to_entity_set(self) -> None:
        """entity_iris에 포함된 subject_iri를 가진 violation만 남아야 한다."""
        v1 = ReasonerViolation(type="CardinalityViolation", subject_iri=E1, description="v1")
        v2 = ReasonerViolation(type="CardinalityViolation", subject_iri=E3, description="v2")
        result = _make_result(violations=[v1, v2])
        filtered = ReasonerService._filter_by_entities(result, [E1, E2])
        assert len(filtered.violations) == 1
        assert filtered.violations[0].subject_iri == E1

    def test_filters_inferred_axioms_subject_or_object(self) -> None:
        """inferred_axioms는 subject 또는 object가 entity_set에 속하면 포함."""
        ax1 = InferredAxiom(subject=E1, predicate="http://ex.org/p", object=E3, inference_rule="HermiT")
        ax2 = InferredAxiom(subject=E3, predicate="http://ex.org/p", object=E3, inference_rule="HermiT")
        result = _make_result(inferred=[ax1, ax2])
        filtered = ReasonerService._filter_by_entities(result, [E1])
        assert len(filtered.inferred_axioms) == 1
        assert filtered.inferred_axioms[0].subject == E1

    def test_empty_entity_iris_filters_all(self) -> None:
        """빈 entity_iris → 모든 violations 제거."""
        v1 = ReasonerViolation(type="DisjointViolation", subject_iri=E1, description="v1")
        result = _make_result(violations=[v1])
        filtered = ReasonerService._filter_by_entities(result, [])
        assert filtered.violations == []

    def test_consistent_flag_updated_after_filter(self) -> None:
        """필터 후 남은 UnsatisfiableClass/DisjointViolation이 있으면 consistent=False."""
        v1 = ReasonerViolation(type="DisjointViolation", subject_iri=E1, description="v1")
        result = _make_result(violations=[v1])
        result = result.model_copy(update={"consistent": True})
        filtered = ReasonerService._filter_by_entities(result, [E1])
        assert filtered.consistent is False


# ══════════════════════════════════════════════════════════════════════════════
# H2: Named Graph 다중 통합
# ══════════════════════════════════════════════════════════════════════════════

class TestGetOntGraphs:
    """_get_ont_graphs가 /inferred 제외 + fallback 동작 검증."""

    @pytest.mark.asyncio
    async def test_returns_all_graphs_except_inferred(self, store_mock: MagicMock) -> None:
        """온톨로지 소속 그래프에서 /inferred를 제외한 목록을 반환해야 한다."""
        store_mock.sparql_select = AsyncMock(return_value=[
            {"g": {"value": f"{ONT_IRI}/kg"}},
            {"g": {"value": f"{ONT_IRI}/import1"}},
        ])
        svc = ReasonerService(store_mock)
        graphs = await svc._get_ont_graphs(ONT_IRI, None)
        assert f"{ONT_IRI}/kg" in graphs
        assert f"{ONT_IRI}/import1" in graphs
        assert f"{ONT_IRI}/inferred" not in graphs

    @pytest.mark.asyncio
    async def test_fallback_to_kg_when_no_graphs_found(self, store_mock: MagicMock) -> None:
        """/kg 포함 그래프가 없을 때 fallback으로 {ont_iri}/kg 반환."""
        store_mock.sparql_select = AsyncMock(return_value=[])
        svc = ReasonerService(store_mock)
        graphs = await svc._get_ont_graphs(ONT_IRI, None)
        assert graphs == [f"{ONT_IRI}/kg"]


class TestBuildCombinedRdfxml:
    """_build_combined_rdfxml이 여러 그래프 트리플을 병합하는지 검증."""

    @pytest.mark.asyncio
    async def test_merges_turtle_from_multiple_graphs(self, store_mock: MagicMock) -> None:
        """두 그래프의 turtle을 병합 → 두 그래프 트리플이 모두 포함된 RDF/XML 반환."""
        ttl_g1 = "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://ex.org/A> a owl:Class .\n"
        ttl_g2 = "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://ex.org/B> a owl:Class .\n"
        store_mock.export_turtle = AsyncMock(side_effect=[ttl_g1, ttl_g2])
        svc = ReasonerService(store_mock)
        rdfxml = await svc._build_combined_rdfxml([f"{ONT_IRI}/g1", f"{ONT_IRI}/g2"], None)
        # 두 클래스 모두 RDF/XML에 포함돼야 함
        assert b"ex.org/A" in rdfxml
        assert b"ex.org/B" in rdfxml
        assert b"rdf:RDF" in rdfxml or b"rdf" in rdfxml

    @pytest.mark.asyncio
    async def test_skips_failed_graph_export(self, store_mock: MagicMock) -> None:
        """한 그래프 export 실패 시 나머지로 계속 진행해야 한다."""
        ttl_ok = "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://ex.org/A> a owl:Class .\n"
        store_mock.export_turtle = AsyncMock(side_effect=[Exception("404"), ttl_ok])
        svc = ReasonerService(store_mock)
        rdfxml = await svc._build_combined_rdfxml([f"{ONT_IRI}/bad", f"{ONT_IRI}/ok"], None)
        assert b"ex.org/A" in rdfxml
