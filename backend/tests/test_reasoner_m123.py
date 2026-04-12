"""
tests/test_reasoner_m123.py — Reasoner M1/M2/M3 개선 검증

M1: reasoner_profile 필드 추가 + 프로파일별 추론기 분기
M2: SPARQL 기반 TransitiveProperty/InverseOf 추론 규칙
M3: FunctionalProperty / minCardinality / inverseOf 위반 탐지 추가
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from models.reasoner import ReasonerResult, ReasonerRunRequest, ReasonerViolation, InferredAxiom
from services.reasoner_service import ReasonerService

ONT_IRI = "https://test.example.org/ontology"
INFERRED_GRAPH = f"{ONT_IRI}/inferred"

# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def store_mock() -> MagicMock:
    mock = MagicMock()
    mock.sparql_select = AsyncMock(return_value=[])
    mock.export_turtle = AsyncMock(return_value="")
    mock.insert_triples = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def svc(store_mock: MagicMock) -> ReasonerService:
    return ReasonerService(store_mock)


# ══════════════════════════════════════════════════════════════════════════════
# M1: reasoner_profile
# ══════════════════════════════════════════════════════════════════════════════

class TestReasonerProfile:
    """ReasonerRunRequest 모델 및 프로파일 분기 검증."""

    def test_request_default_profile_is_owl_dl(self) -> None:
        """ReasonerRunRequest의 기본 reasoner_profile은 OWL_DL이어야 한다."""
        req = ReasonerRunRequest()
        assert req.reasoner_profile == "OWL_DL"

    def test_request_accepts_all_profiles(self) -> None:
        """모든 프로파일 값이 허용돼야 한다."""
        for profile in ("OWL_DL", "OWL_EL", "OWL_RL", "OWL_QL"):
            req = ReasonerRunRequest(reasoner_profile=profile)
            assert req.reasoner_profile == profile

    def test_request_rejects_invalid_profile(self) -> None:
        """유효하지 않은 프로파일은 ValidationError를 발생시켜야 한다."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ReasonerRunRequest(reasoner_profile="OWL_INVALID")

    def test_dispatch_owl_dl_calls_hermit(self, svc: ReasonerService) -> None:
        """OWL_DL 프로파일 → _run_hermit 호출."""
        dummy_result = ReasonerResult(consistent=True, violations=[], inferred_axioms=[], execution_ms=1)
        with patch.object(svc, "_run_hermit", return_value=dummy_result) as mock_hermit:
            result = svc._dispatch_reasoner("/tmp/test.owl", "OWL_DL")
        mock_hermit.assert_called_once_with("/tmp/test.owl")
        assert result is dummy_result

    def test_dispatch_owl_el_calls_pellet(self, svc: ReasonerService) -> None:
        """OWL_EL 프로파일 → _run_pellet 호출."""
        dummy_result = ReasonerResult(consistent=True, violations=[], inferred_axioms=[], execution_ms=1)
        with patch.object(svc, "_run_pellet", return_value=dummy_result) as mock_pellet:
            result = svc._dispatch_reasoner("/tmp/test.owl", "OWL_EL")
        mock_pellet.assert_called_once_with("/tmp/test.owl")
        assert result is dummy_result

    def test_dispatch_owl_rl_skips_owlready2(self, svc: ReasonerService) -> None:
        """OWL_RL 프로파일 → owlready2 없이 빈 결과 반환."""
        result = svc._dispatch_reasoner("/tmp/test.owl", "OWL_RL")
        assert result.consistent is True
        assert result.violations == []
        assert result.inferred_axioms == []

    def test_dispatch_owl_ql_skips_owlready2(self, svc: ReasonerService) -> None:
        """OWL_QL 프로파일 → owlready2 없이 빈 결과 반환."""
        result = svc._dispatch_reasoner("/tmp/test.owl", "OWL_QL")
        assert result.consistent is True


# ══════════════════════════════════════════════════════════════════════════════
# M2: SPARQL 추론 규칙 (TransitiveProperty / InverseOf)
# ══════════════════════════════════════════════════════════════════════════════

class TestSparqlInferenceRules:
    """_apply_sparql_inference_rules 검증."""

    @pytest.mark.asyncio
    async def test_transitive_property_inserts_closure(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """TransitiveProperty를 가진 프로퍼티에 대해 추이 클로저 트리플을 삽입해야 한다."""
        PROP = "https://ex.org/hasPart"
        A, B, C = "https://ex.org/A", "https://ex.org/B", "https://ex.org/C"

        # sparql_select 호출 순서:
        # 1) TransitiveProperty 목록
        # 2) 해당 prop의 추이 클로저 쌍
        # 3) InverseOf 쌍 (없음)
        store_mock.sparql_select = AsyncMock(side_effect=[
            [{"p": {"value": PROP}}],          # TransitiveProperty 목록
            [                                   # prop 추이 클로저: A→C (A→B, B→C 존재)
                {"a": {"value": A}, "c": {"value": C}},
            ],
            [],                                 # InverseOf 쌍 없음
        ])

        axioms = await svc._apply_sparql_inference_rules(ONT_IRI, None)

        assert len(axioms) == 1
        assert axioms[0].subject == A
        assert axioms[0].predicate == PROP
        assert axioms[0].object == C
        assert axioms[0].inference_rule == "TransitiveProperty"
        # inferred graph에 insert 호출 확인
        store_mock.insert_triples.assert_called()

    @pytest.mark.asyncio
    async def test_inverse_of_inserts_reverse_triple(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """owl:inverseOf 선언에 따라 역방향 트리플을 삽입해야 한다."""
        PROP = "https://ex.org/hasParent"
        INV  = "https://ex.org/hasChild"
        A, B = "https://ex.org/Alice", "https://ex.org/Bob"

        store_mock.sparql_select = AsyncMock(side_effect=[
            [],   # TransitiveProperty 없음
            [     # InverseOf 쌍: (hasParent, hasChild) → Alice hasParent Bob, 역방향 Bob hasChild Alice 누락
                {"p": {"value": PROP}, "q": {"value": INV}, "a": {"value": A}, "b": {"value": B}},
            ],
        ])

        axioms = await svc._apply_sparql_inference_rules(ONT_IRI, None)

        assert any(
            ax.subject == B and ax.predicate == INV and ax.object == A
            for ax in axioms
        ), f"Expected inverse triple B-{INV}-A, got: {axioms}"

    @pytest.mark.asyncio
    async def test_no_rules_returns_empty(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """TransitiveProperty/InverseOf가 없으면 빈 axiom 목록 반환."""
        store_mock.sparql_select = AsyncMock(return_value=[])
        axioms = await svc._apply_sparql_inference_rules(ONT_IRI, None)
        assert axioms == []
        store_mock.insert_triples.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# M3: 추가 위반 탐지 (FunctionalProperty / minCardinality / inverseOf)
# ══════════════════════════════════════════════════════════════════════════════

class TestFunctionalPropertyViolations:
    """_detect_functional_property_violations 검증."""

    @pytest.mark.asyncio
    async def test_detects_functional_property_duplicate(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """FunctionalProperty에 2개 이상의 값을 가진 개체 → 위반 반환."""
        IND = "https://ex.org/Bob"
        PROP = "https://ex.org/hasSSN"
        store_mock.sparql_select = AsyncMock(return_value=[
            {"ind": {"value": IND}, "prop": {"value": PROP}, "cnt": {"value": "2"}},
        ])

        violations = await svc._detect_functional_property_violations(ONT_IRI, None)

        assert len(violations) == 1
        v = violations[0]
        assert v.type == "FunctionalPropertyViolation"
        assert v.subject_iri == IND
        assert PROP in v.description

    @pytest.mark.asyncio
    async def test_no_violation_when_single_value(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """FunctionalProperty 값이 1개이면 위반 없음."""
        store_mock.sparql_select = AsyncMock(return_value=[])
        violations = await svc._detect_functional_property_violations(ONT_IRI, None)
        assert violations == []


class TestMinCardinalityViolations:
    """_detect_min_cardinality_violations 검증."""

    @pytest.mark.asyncio
    async def test_detects_below_min_cardinality(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """minCardinality=2인 프로퍼티에 1개만 있는 개체 → 위반 반환."""
        CLS  = "https://ex.org/Person"
        PROP = "https://ex.org/hasContact"
        IND  = "https://ex.org/Alice"
        store_mock.sparql_select = AsyncMock(return_value=[
            {"cls": {"value": CLS}, "prop": {"value": PROP}, "n": {"value": "2"},
             "ind": {"value": IND}, "cnt": {"value": "1"}},
        ])

        violations = await svc._detect_min_cardinality_violations(ONT_IRI, None)

        assert len(violations) == 1
        v = violations[0]
        assert v.type == "CardinalityViolation"
        assert v.subject_iri == IND
        assert "minCardinality" in v.description

    @pytest.mark.asyncio
    async def test_no_violation_when_meets_min(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """minCardinality 충족 시 위반 없음."""
        store_mock.sparql_select = AsyncMock(return_value=[])
        violations = await svc._detect_min_cardinality_violations(ONT_IRI, None)
        assert violations == []


class TestInverseOfViolations:
    """_detect_inverse_of_violations 검증."""

    @pytest.mark.asyncio
    async def test_detects_missing_inverse_triple(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """inverseOf 선언됐으나 역방향 트리플 누락 → 위반 반환."""
        A = "https://ex.org/Alice"
        B = "https://ex.org/Bob"
        PROP = "https://ex.org/hasParent"
        INV  = "https://ex.org/hasChild"
        store_mock.sparql_select = AsyncMock(return_value=[
            {"a": {"value": A}, "p": {"value": PROP}, "b": {"value": B},
             "q": {"value": INV}},
        ])

        violations = await svc._detect_inverse_of_violations(ONT_IRI, None)

        assert len(violations) == 1
        v = violations[0]
        assert v.type == "InverseOfViolation"
        assert A in v.description or B in v.description

    @pytest.mark.asyncio
    async def test_no_violation_when_inverse_exists(self, svc: ReasonerService, store_mock: MagicMock) -> None:
        """역방향 트리플이 이미 존재하면 위반 없음."""
        store_mock.sparql_select = AsyncMock(return_value=[])
        violations = await svc._detect_inverse_of_violations(ONT_IRI, None)
        assert violations == []
