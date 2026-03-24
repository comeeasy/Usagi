# 디버그 로그: 테스트 과정에서 발견된 이슈

**작성일:** 2026-03-25
**테스트 단계:** Phase 1 — 백엔드 단위/통합 테스트

---

## 이슈 목록

---

### [BUG-001] `api/sources.py` — `from __future__ import annotations` + FastAPI 204 충돌

**발견 시점:** Phase 1 준비 — 앱 임포트 테스트
**심각도:** 🔴 Critical (앱 전체 기동 불가)
**파일:** `backend/api/sources.py:12`

**증상:**
```
AssertionError: Status code 204 must not have a response body
```
`main.py`를 임포트하면 `sources.py` 로드 시 즉시 크래시.

**원인 분석:**
`sources.py`에만 `from __future__ import annotations`가 있음 (다른 API 파일에는 없음).
이 선언은 모든 어노테이션을 lazy string으로 변환하며,
FastAPI 0.111.1이 `-> None` return type을 응답 모델로 잘못 해석해
`status_code=204`와 충돌하는 AssertionError 발생.

**재현:**
```bash
python -c "from api.sources import router"
# AssertionError: Status code 204 must not have a response body
```

**다른 파일 비교:**
- `api/ontologies.py`, `api/concepts.py`, `api/properties.py` 모두 동일한 `status_code=204, -> None` 패턴이지만 `from __future__ import annotations` 없으므로 정상 동작

**할 일:**
- `backend/api/sources.py`에서 `from __future__ import annotations` 제거 (라인 12)

---

### [BUG-002] `backend/tests/conftest.py` — 모든 Fixture가 `NotImplementedError`

**발견 시점:** Phase 1 — `pytest` 최초 실행
**심각도:** 🔴 Critical (Phase 1 테스트 전체 실행 불가)
**파일:** `backend/tests/conftest.py`

**증상:**
```
ERROR tests/test_concepts.py::test_create_concept - NotImplementedError
ERROR tests/test_ontologies.py::test_create_ontology - NotImplementedError
(총 10개 ERROR)
```

**원인 분석:**
`conftest.py`의 `app`, `client`, `ontology_store` fixture가 모두 구현 없이 `raise NotImplementedError`만 있음.

**할 일:**
- `conftest.py` 구현:
  - `ontology_store`: `OntologyStore(path=None)` 인메모리 인스턴스
  - `mock_graph_store`: `AsyncMock(spec=GraphStore)`
  - `mock_kafka_producer`: `MagicMock(spec=KafkaProducer)`
  - `app`: `main.app`에 state 오버라이드 (BUG-001 수정 후)
  - `client`: `httpx.AsyncClient(app=app, base_url="http://test/api/v1")`

---

### [BUG-003] `pytest.ini` 없음 — asyncio_mode 미설정

**발견 시점:** Phase 1 — pytest 실행 환경 점검
**심각도:** 🟡 Medium (테스트 실행 시 경고 또는 동작 불일치 가능)
**파일:** 없음 (미생성)

**증상:**
pytest 실행 시 `asyncio: mode=Mode.STRICT` 로 기본 동작.
test 파일들은 `@pytest.mark.asyncio`를 사용하므로 현재는 strict 모드에서도 동작 가능하지만,
fixture loop scope 설정 없이 warning 발생 가능.

**할 일:**
`backend/pytest.ini` 생성:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

---

### [BUG-004] `models/reasoner.py` — `JobResponse` 클래스 누락

**발견 시점:** Phase 1 — 모델 임포트 테스트
**심각도:** 🟡 Medium (Reasoner/Sources 테스트 작성 시 영향)
**파일:** `backend/models/reasoner.py`

**증상:**
```python
from models.reasoner import JobResponse
# ImportError: cannot import name 'JobResponse' from 'models.reasoner'
```

**원인 분석:**
`models/reasoner.py`에 정의된 클래스: `ReasonerResult`, `ReasonerViolation`, `InferredAxiom`, `ReasonerJob`, `ReasonerRunRequest`
`JobResponse`는 설계서(specification.md §3.2)에 명시되어 있으나 미구현.

**할 일:**
`backend/models/reasoner.py`에 `JobResponse` 클래스 추가:
```python
class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
```

---

### [BUG-005] `OntologyStore.sparql_select()` 시그니처 — `ontology_id` 파라미터 없음

**발견 시점:** Phase 1 — OntologyStore 직접 테스트
**심각도:** 🟢 Low (API 테스트에는 영향 없음, 테스트 계획서 수정 필요)
**파일:** `backend/services/ontology_store.py:94`

**증상:**
```python
await store.sparql_select(ontology_id, query)
# TypeError: OntologyStore.sparql_select() takes 2 positional arguments but 3 were given
```

**원인 분석:**
실제 시그니처: `sparql_select(self, query: str)` — `ontology_id` 없음
`test.md`의 테스트 계획서에 `ontology_id` 전달하는 것으로 잘못 기술됨.

**할 일:**
`docs/test.md` Phase 2 OntologyStore 테스트 케이스에서 `ontology_id` 제거.
테스트 코드 작성 시 `store.sparql_select(query)` 형태로 호출.

---

### [INFO-001] `OntologyStore` — `create_ontology` 헬퍼 메서드 없음 (의도된 설계)

**발견 시점:** Phase 1 — OntologyStore 직접 테스트
**심각도:** 🟢 Low (설계대로 동작, 문서화 목적)
**파일:** `backend/services/ontology_store.py`

**내용:**
`OntologyStore`에 `create_ontology()` 헬퍼 없음.
`api/ontologies.py`는 `sparql_update()`로 직접 SPARQL INSERT DATA를 실행해 온톨로지 생성.
설계대로이며 버그 아님. API 통합 테스트(Phase 1)에서 `client.post()`로 검증해야 함.

---

### [INFO-002] MCP 7종 도구 — 임포트 및 기본 호출 정상 동작 확인

**발견 시점:** Phase 1 준비 — MCP 환경 점검
**심각도:** 🟢 Info (정상)
**파일:** `backend/app_mcp/tools.py`

**내용:**
```python
tools = await mcp.list_tools()
# → ['list_ontologies', 'get_ontology_summary', 'search_entities',
#    'search_relations', 'get_subgraph', 'sparql_query', 'run_reasoner']
```
7종 도구 모두 등록 확인. `init_services()` 호출 + 인메모리 Store 연결 시 `list_ontologies` 정상 반환.

---

## 현재 Phase 1 진행 상태

| 항목 | 상태 | 블로커 |
|------|------|--------|
| 의존성 설치 (pytest, httpx 등) | ✅ 완료 | — |
| 앱 임포트 | ❌ 실패 | BUG-001 |
| conftest.py fixture | ❌ 미구현 | BUG-002 |
| pytest.ini 설정 | ❌ 없음 | BUG-003 |
| 온톨로지 API 테스트 실행 | ⏸ 대기 | BUG-001, BUG-002 |
| Concept API 테스트 실행 | ⏸ 대기 | BUG-001, BUG-002 |
| OntologyStore 직접 동작 | ✅ 정상 | — |
| MCP 도구 임포트/기본 호출 | ✅ 정상 | — |

**Phase 1 진행을 위한 필수 수정 우선순위:**
1. BUG-001: `api/sources.py` `from __future__ import annotations` 제거
2. BUG-002: `conftest.py` 구현
3. BUG-003: `pytest.ini` 생성

---

*이 파일은 테스트 진행 중 계속 업데이트됩니다.*
