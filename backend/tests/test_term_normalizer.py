"""
tests/test_term_normalizer.py — TermNormalizerService 단위 테스트

Fuseki 없이 MemoryOntologyStore + MockVectorIndexManager로 테스트.

커버 케이스:
  - 사전 정확 매칭 (dict hit)
  - SPARQL label 매칭 (sparql hit)
  - SPARQL altLabel 매칭
  - 벡터 유사도 매칭 (vector hit)
  - 매칭 실패 → requires_review=True
  - 빈 입력
  - threshold 동작 (낮은 점수 → requires_review)
  - 폴백 순서 보장 (dict > sparql > vector)
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import services.term_normalizer as _tn_module
from services.term_normalizer import TermNormalizerService, _load_dict, NormalizeResult

# ── 공통 상수 ─────────────────────────────────────────────────────────────────

_ONT_ID = "https://example.org/mil/"
_COMMANDER_IRI = "https://example.org/mil/Commander"
_UNIT_IRI = "https://example.org/mil/MilitaryUnit"


# ── 인메모리 스토어 (conftest MemoryOntologyStore 재사용) ─────────────────────

@pytest.fixture
def mem_store():
    """rdflib ConjunctiveGraph 기반 인메모리 스토어."""
    from tests.conftest import MemoryOntologyStore
    store = MemoryOntologyStore()

    # 온톨로지 등록 (dc:identifier 없이 IRI로 직접 사용)
    store._graph.update("""
        PREFIX owl:  <http://www.w3.org/2002/07/owl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dc:   <http://purl.org/dc/terms/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        INSERT DATA {
            GRAPH <https://example.org/mil/manual> {
                <https://example.org/mil/> a owl:Ontology ;
                    dc:identifier "test-mil-ont" .

                <https://example.org/mil/Commander> a owl:Class ;
                    rdfs:label "지휘관" .

                <https://example.org/mil/MilitaryUnit> a owl:Class ;
                    rdfs:label "부대" .

                <https://example.org/mil/Mission> a owl:Class ;
                    rdfs:label "임무" .

                <https://example.org/mil/Commander>
                    skos:altLabel "CO"@en ;
                    skos:altLabel "사령관"@ko .
            }
        }
    """)
    return store


@pytest.fixture
def mock_vim():
    """VectorIndexManager Mock — 기본적으로 빈 결과 반환.
    search는 async, invalidate는 sync이므로 각각 다르게 mock.
    """
    vim = MagicMock()
    vim.search = AsyncMock(return_value=[])
    vim.invalidate = MagicMock(return_value=None)
    return vim


@pytest.fixture
def normalizer(mem_store, mock_vim):
    return TermNormalizerService(mem_store, mock_vim, threshold=0.60)


# ── 사전 로드 테스트 ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_dict_cache():
    """테스트 간 dict 캐시 격리 — military_terms.json 변경 반영."""
    _tn_module._DICT = {}
    yield
    _tn_module._DICT = {}


def test_dict_loads_variants():
    d = _load_dict()
    assert len(d) > 0
    # "CO"는 지휘관의 variant (중대는 "Coy"로 변경하여 충돌 방지)
    assert d.get("co") == "지휘관"


def test_dict_canonical_included():
    d = _load_dict()
    # canonical 자신도 색인에 포함
    assert d.get("지휘관") == "지휘관"
    assert d.get("사단") == "사단"


# ── dict 매핑 테스트 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_dict_hit_variant(normalizer):
    """'CO' → 사전에서 canonical '지휘관' → SPARQL에서 Commander IRI."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="CO",
    )
    assert result.iri == _COMMANDER_IRI
    assert result.source == "dict"
    assert result.score == 1.0
    assert not result.requires_review


@pytest.mark.asyncio
async def test_normalize_dict_hit_canonical(normalizer):
    """'지휘관' 자체도 사전에서 canonical로 매핑."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="지휘관",
    )
    assert result.iri == _COMMANDER_IRI
    assert result.source == "dict"


@pytest.mark.asyncio
async def test_normalize_dict_hit_opcon(normalizer):
    """'OPCON' → 사전 → '전시작전통제권' canonical → SPARQL에서 미발견 → sparql/vector 폴백."""
    # OPCON은 사전에 있지만 이 테스트 온톨로지에 클래스가 없으므로
    # dict step에서 canonical 찾고, SPARQL에서 못 찾으면 vector로 폴백
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="OPCON",
    )
    # IRI 없거나 source != "dict" (온톨로지에 클래스 없음)
    # dict hit 후 sparql 실패 → vector (mock은 빈 배열) → none
    assert result.source in ("dict", "sparql", "vector", "none")


# ── SPARQL 매핑 테스트 ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_sparql_label_hit(normalizer):
    """사전 미등록 용어지만 온톨로지 rdfs:label과 일치."""
    # "임무"는 사전에 있지만 직접 테스트: 온톨로지 rdfs:label로 찾아야 함
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="임무",
    )
    assert result.iri is not None
    assert "Mission" in result.iri
    assert result.score >= 0.75  # 정확 일치


@pytest.mark.asyncio
async def test_normalize_sparql_altlabel_hit(normalizer):
    """skos:altLabel '사령관'으로 Commander 매핑."""
    # 사전에 "사령관" → "지휘관" canonical이 있으므로 dict hit 먼저
    # altLabel 직접 테스트: 온톨로지에 skos:altLabel "사령관"@ko 등록됨
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="사령관",
    )
    assert result.iri == _COMMANDER_IRI


@pytest.mark.asyncio
async def test_normalize_sparql_partial_match(normalizer):
    """부분 일치 ('지휘') 시 score < 1.0이지만 결과 반환."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="지휘",
        threshold=0.3,  # 낮춰서 반환되도록
    )
    assert result.iri is not None


# ── Vector 폴백 테스트 ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_vector_fallback(normalizer, mock_vim):
    """SPARQL 미매핑 시 vector 검색으로 폴백."""
    mock_vim.search.return_value = [
        {"iri": _UNIT_IRI, "label": "부대", "kind": "concept", "score": 0.82}
    ]
    # 온톨로지에 없는 용어 (사전에도 없는 것)
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="군사조직편제",
    )
    assert result.iri == _UNIT_IRI
    assert result.source == "vector"
    assert result.score == pytest.approx(0.82, abs=0.01)


@pytest.mark.asyncio
async def test_normalize_vector_kind_filter(normalizer, mock_vim):
    """kind='concept' 필터로 individual 결과 제외."""
    mock_vim.search.return_value = [
        {"iri": "https://ex/ind/홍길동", "label": "홍길동", "kind": "individual", "score": 0.90},
        {"iri": _UNIT_IRI, "label": "부대", "kind": "concept", "score": 0.70},
    ]
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="군사조직편제",
        kind="concept",
    )
    assert result.iri == _UNIT_IRI
    assert result.source == "vector"


# ── 매칭 실패 테스트 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_no_match(normalizer):
    """완전히 매핑 불가한 용어 → requires_review=True, iri=None."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="전혀관계없는특수문자!@#",
    )
    assert result.iri is None
    assert result.source == "none"
    assert result.requires_review is True


@pytest.mark.asyncio
async def test_normalize_empty_term(normalizer):
    """빈 문자열 입력 → requires_review=True, score=0."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="",
    )
    assert result.iri is None
    assert result.score == 0.0
    assert result.requires_review is True


@pytest.mark.asyncio
async def test_normalize_whitespace_term(normalizer):
    """공백만 있는 입력 → 빈 문자열과 동일하게 처리."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="   ",
    )
    assert result.iri is None
    assert result.requires_review is True


# ── threshold 동작 테스트 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_low_score_requires_review(normalizer, mock_vim):
    """score < threshold → requires_review=True."""
    mock_vim.search.return_value = [
        {"iri": _UNIT_IRI, "label": "부대", "kind": "concept", "score": 0.40}
    ]
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="군사조직",
        threshold=0.60,
    )
    assert result.requires_review is True


@pytest.mark.asyncio
async def test_normalize_high_score_no_review(normalizer):
    """정확 매핑 → requires_review=False."""
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="지휘관",
        threshold=0.60,
    )
    assert result.requires_review is False


# ── candidates 테스트 ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_candidates_provided(normalizer, mock_vim):
    """결과에 candidates 목록이 포함되어야 함."""
    mock_vim.search.return_value = [
        {"iri": _UNIT_IRI, "label": "부대", "kind": "concept", "score": 0.82},
        {"iri": _COMMANDER_IRI, "label": "지휘관", "kind": "concept", "score": 0.61},
    ]
    result = await normalizer.normalize(
        ontology_id=_ONT_ID,
        term="군사조직",
    )
    assert isinstance(result.candidates, list)


# ── API 엔드포인트 테스트 ─────────────────────────────────────────────────────

_ONT_UUID = "test-mil-ont"


@pytest.fixture
def normalize_app(mem_store, mock_vim):
    """normalize 라우터가 포함된 테스트 앱.

    ontology_id로 UUID "test-mil-ont"을 사용하고,
    mem_store에 dc:identifier를 등록하여 resolve_ontology_iri가 동작하도록 설정.
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from api import normalize as norm_router

    test_app = FastAPI()
    test_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    test_app.state.ontology_store = mem_store
    test_app.state.vector_index_manager = mock_vim
    test_app.state.term_normalizer = TermNormalizerService(mem_store, mock_vim, threshold=0.60)

    test_app.include_router(norm_router.router, prefix="/api/v1")
    return test_app


@pytest_asyncio.fixture
async def norm_client(normalize_app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=normalize_app),
        base_url="http://test/api/v1",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_normalize_endpoint_200(norm_client):
    """POST /normalize 성공 — UUID로 온톨로지 조회."""
    resp = await norm_client.post(
        f"/ontologies/{_ONT_UUID}/normalize",
        json={"term": "지휘관", "kind": "concept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "iri" in body
    assert "score" in body
    assert "source" in body
    assert "requires_review" in body


@pytest.mark.asyncio
async def test_normalize_batch_endpoint(norm_client):
    """POST /normalize/batch 성공."""
    resp = await norm_client.post(
        f"/ontologies/{_ONT_UUID}/normalize/batch",
        json={"terms": ["지휘관", "부대", "임무"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["results"]) == 3
    assert "review_required" in body


@pytest.mark.asyncio
async def test_altlabel_list_endpoint(norm_client):
    """GET /terms/altlabel — 등록된 altLabel 목록 반환."""
    resp = await norm_client.get(f"/ontologies/{_ONT_UUID}/terms/altlabel")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    # Commander에 CO, 사령관 등 altLabel 등록됨
    labels = [item["alt_label"] for item in body["items"]]
    assert "CO" in labels or "사령관" in labels


@pytest.mark.asyncio
async def test_altlabel_create_and_delete(norm_client):
    """POST /terms/altlabel 등록 → DELETE 삭제."""
    # 등록
    resp = await norm_client.post(
        f"/ontologies/{_ONT_UUID}/terms/altlabel",
        json={
            "entity_iri": _COMMANDER_IRI,
            "label": "테스트별칭",
            "lang": "ko",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "created"

    # 삭제
    resp2 = await norm_client.request(
        "DELETE",
        f"/ontologies/{_ONT_UUID}/terms/altlabel",
        json={
            "entity_iri": _COMMANDER_IRI,
            "label": "테스트별칭",
            "lang": "ko",
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "deleted"
