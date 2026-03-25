# 테스트 계획서: Palantir Foundry 온톨로지 플랫폼

**작성일:** 2026-03-25
**버전:** 1.0
**기반 설계서:** docs/specification.md v1.0

---

## 목차

1. [테스트 전략](#1-테스트-전략)
2. [테스트 환경 설정](#2-테스트-환경-설정)
3. [Phase 1 — 백엔드 단위/통합 테스트](#3-phase-1--백엔드-단위통합-테스트)
4. [Phase 2 — 서비스 레이어 단위 테스트](#4-phase-2--서비스-레이어-단위-테스트)
5. [Phase 3 — MCP 도구 테스트](#5-phase-3--mcp-도구-테스트)
6. [Phase 4 — 프론트엔드 컴포넌트 테스트](#6-phase-4--프론트엔드-컴포넌트-테스트)
7. [Phase 5 — E2E 테스트](#7-phase-5--e2e-테스트)
8. [실행 방법](#8-실행-방법)
9. [커버리지 목표](#9-커버리지-목표)

---

## 1. 테스트 전략

### 1.1 레이어별 접근 방식

| 레이어 | 도구 | 의존성 처리 |
|--------|------|------------|
| 백엔드 API (통합) | pytest + httpx AsyncClient | Oxigraph 인메모리, Neo4j/Kafka Mock |
| 서비스 레이어 (단위) | pytest + pytest-asyncio | Oxigraph 인메모리, 외부 서비스 Mock |
| MCP 도구 (단위) | pytest + pytest-asyncio | 서비스 레이어 Mock |
| 프론트엔드 컴포넌트 | Vitest + React Testing Library | API Mock (MSW) |
| E2E | Playwright | Docker Compose 전체 스택 |

### 1.2 핵심 원칙

- **Oxigraph는 실제 인메모리 인스턴스 사용**: `OntologyStore(path=None)` → 빠르고 격리된 테스트
- **Neo4j/Kafka는 Mock 처리**: 외부 의존성 제거, CI 환경에서도 실행 가능
- **각 테스트는 독립적**: fixture에서 Store를 새로 생성, 테스트 간 상태 공유 없음
- **API 테스트는 실제 HTTP 요청**: httpx.AsyncClient로 FastAPI TestClient 대체

### 1.3 우선순위

```
Phase 1 (필수) → Phase 2 (중요) → Phase 3 (중요) → Phase 4 (선택) → Phase 5 (선택)
```

---

## 2. 테스트 환경 설정

### 2.1 필요 패키지 (`backend/requirements-test.txt`)

```
pytest==8.x
pytest-asyncio==0.23.x
httpx==0.27.x
pytest-cov==5.x
```

### 2.2 `conftest.py` 구현 계획

```python
# backend/tests/conftest.py

@pytest_asyncio.fixture
async def ontology_store():
    """인메모리 Oxigraph OntologyStore — 각 테스트마다 새 인스턴스."""
    store = OntologyStore(path=None)   # path=None → pyoxigraph.Store() 인메모리
    yield store
    # 별도 cleanup 불필요 (GC 처리)

@pytest_asyncio.fixture
def mock_graph_store():
    """Neo4j GraphStore Mock — 실제 DB 연결 없음."""
    mock = AsyncMock(spec=GraphStore)
    mock.get_subgraph.return_value = {"nodes": [], "edges": []}
    mock.sync_from_oxigraph.return_value = None
    return mock

@pytest_asyncio.fixture
def mock_kafka_producer():
    """Kafka KafkaProducer Mock."""
    mock = MagicMock(spec=KafkaProducer)
    mock.send.return_value = None
    return mock

@pytest_asyncio.fixture
async def app(ontology_store, mock_graph_store, mock_kafka_producer):
    """테스트용 FastAPI 앱 — 의존성 오버라이드 적용."""
    from main import create_app   # 또는 직접 FastAPI() 구성
    application = create_app()
    application.state.ontology_store = ontology_store
    application.state.graph_store = mock_graph_store
    application.state.kafka_producer = mock_kafka_producer
    yield application

@pytest_asyncio.fixture
async def client(app):
    """httpx AsyncClient."""
    async with AsyncClient(app=app, base_url="http://test/api/v1") as ac:
        yield ac

@pytest_asyncio.fixture
async def created_ontology(client):
    """테스트용 온톨로지 사전 생성 — 다른 리소스 테스트의 선행 조건."""
    resp = await client.post("/ontologies", json={
        "label": "Test Ontology",
        "iri": "https://test.example.org/onto",
        "description": "테스트용"
    })
    return resp.json()
```

### 2.3 `pytest.ini` 설정

```ini
[pytest]
asyncio_mode = auto
testpaths = backend/tests
python_files = test_*.py
python_functions = test_*
```

---

## 3. Phase 1 — 백엔드 단위/통합 테스트

API 엔드포인트를 httpx AsyncClient로 직접 호출하는 통합 테스트.

### 3.1 온톨로지 CRUD (`test_ontologies.py`)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_create_ontology` | POST 201, id/iri/label 반환 |
| `test_create_ontology_duplicate_iri` | POST 409 Conflict |
| `test_list_ontologies_empty` | GET 200, items=[], total=0 |
| `test_list_ontologies_paginated` | GET 200, page/pageSize/total 정확성 |
| `test_get_ontology` | GET 200, stats 포함 확인 |
| `test_get_ontology_not_found` | GET 404 |
| `test_update_ontology` | PUT 200, label/description 변경 확인 |
| `test_delete_ontology` | DELETE 204 → 이후 GET 404 |
| `test_delete_ontology_clears_concepts` | 삭제 후 소속 Concept도 사라짐 |

### 3.2 Concept CRUD (`test_concepts.py`)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_create_concept` | POST 201, iri/label 반환 |
| `test_create_concept_invalid_iri` | POST 422 (IRI 형식 오류) |
| `test_create_concept_duplicate` | POST 409 |
| `test_list_concepts` | GET 200, items 구조 확인 |
| `test_list_concepts_search` | `?search=Foo` → 라벨 CONTAINS 필터 |
| `test_get_concept_with_restrictions` | restrictions 배열 포함 |
| `test_update_concept_label` | PUT 200, label 변경 |
| `test_update_concept_parent` | parent_iris 변경 후 superClasses 반영 |
| `test_delete_concept` | DELETE 204 → 이후 GET 404 |

### 3.3 Individual CRUD (`test_individuals.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_create_individual_manual` | POST 201, Named Graph = manual/{uuid} |
| `test_create_individual_with_types` | type_iris → rdf:type 트리플 확인 |
| `test_create_individual_with_data_props` | data_properties 값 저장 |
| `test_list_individuals_filter_by_type` | `?type_iri=...` 필터 |
| `test_get_individual_provenance` | GET /{iri}/provenance → ProvenanceRecord |
| `test_update_individual` | PUT 200, user-edit-wins 정책 |
| `test_delete_individual` | DELETE 204 |

### 3.4 Property CRUD (`test_properties.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_create_object_property` | POST /properties/object 201 |
| `test_create_data_property` | POST /properties/data 201 |
| `test_list_object_properties` | GET, kind=object |
| `test_list_data_properties` | GET, kind=data |
| `test_list_properties_search` | `?search=has` 필터 |
| `test_update_object_property_characteristics` | characteristics 변경 |
| `test_update_data_property_range` | range(xsd:*) 변경 |
| `test_delete_property` | DELETE 204 |

### 3.5 검색 API (`test_search.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_search_entities_by_label` | `?q=Person` → Concept 반환 |
| `test_search_entities_kind_filter` | `?kind=concept` / `?kind=individual` |
| `test_search_entities_empty_result` | 존재하지 않는 키워드 → items=[] |
| `test_search_relations_by_label` | `?q=has` → Property 반환 |
| `test_search_relations_domain_filter` | `?domain_iri=...` 필터 |

### 3.6 SPARQL API (`test_sparql.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_sparql_select_all_classes` | SELECT ?c WHERE { ?c rdf:type owl:Class } → 결과 목록 |
| `test_sparql_ask` | ASK { ... } → boolean |
| `test_sparql_syntax_error` | 잘못된 쿼리 → 400 SPARQL_SYNTAX_ERROR |
| `test_sparql_update_blocked` | UPDATE 쿼리 → 403 |

### 3.7 Import API (`test_import.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_import_turtle_file` | .ttl 업로드 → Concept이 온톨로지에 추가됨 |
| `test_import_owl_file` | .owl(RDF/XML) 업로드 → 파싱 성공 |
| `test_import_invalid_format` | 지원하지 않는 형식 → 400 |
| `test_import_standard_foaf` | body={name:"foaf"} → FOAF 온톨로지 로드 |

### 3.8 Merge API (`test_merge.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_merge_preview_no_conflict` | 충돌 없는 두 온톨로지 → conflicts=[] |
| `test_merge_preview_with_conflict` | 동일 IRI 다른 domain → 충돌 리포트 |
| `test_merge_execute` | POST /merge → 두 온톨로지의 Concept이 하나로 합쳐짐 |

### 3.9 Reasoner API (`test_reasoner.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_reasoner_run_returns_job_id` | POST /reasoner/run → 202 + jobId |
| `test_reasoner_job_status_pending` | GET /reasoner/jobs/{id} → status=pending or running |
| `test_reasoner_consistent_ontology` | 단순 온톨로지 → consistent=true, violations=[] |
| `test_reasoner_inconsistent_ontology` | 모순 클래스 → consistent=false, violations 포함 |

### 3.10 Backing Sources API (`test_sources.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_create_source_jdbc` | POST /sources, type=jdbc → 201 |
| `test_create_source_api_rest` | POST /sources, type=api-rest → 201 |
| `test_list_sources` | GET /sources → 목록 |
| `test_update_source` | PUT /sources/{id} → 설정 변경 |
| `test_delete_source` | DELETE /sources/{id} → 204 |
| `test_trigger_sync` | POST /sources/{id}/sync → JobResponse |

---

## 4. Phase 2 — 서비스 레이어 단위 테스트

### 4.1 OntologyStore (`test_service_ontology_store.py` — 신규 파일)

OntologyStore는 핵심 저장소이므로 독립적으로 검증.

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_store_init_in_memory` | `OntologyStore(path=None)` 초기화 성공 |
| `test_insert_and_select_triples` | insert_triples → sparql_select로 읽기 |
| `test_sparql_select_returns_dict` | NamedNode/Literal/BlankNode → 올바른 type/value 변환 |
| `test_sparql_update_insert` | SPARQL INSERT DATA → 트리플 추가 확인 |
| `test_sparql_update_delete` | SPARQL DELETE DATA → 트리플 제거 확인 |
| `test_delete_graph` | Named Graph 삭제 → 해당 그래프 트리플 없어짐 |
| `test_export_turtle` | export_turtle → 유효한 Turtle 문자열 반환 |
| `test_get_ontology_stats` | concepts/individuals/properties 카운트 정확성 |
| `test_sparql_syntax_error_raises` | 잘못된 쿼리 → SparqlSyntaxError 예외 |
| `test_sparql_timeout` | 매우 복잡한 쿼리 → 타임아웃 처리 |

### 4.2 SearchService (`test_service_search.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_keyword_search_entities_concept` | label CONTAINS → Concept 반환 |
| `test_keyword_search_entities_individual` | Individual 검색 |
| `test_keyword_search_case_insensitive` | 대소문자 구분 없음 |
| `test_search_relations_by_domain` | domain_iri 필터 |
| `test_search_empty` | 없는 키워드 → 빈 리스트 |

### 4.3 IRI 생성기 (`test_service_iri_generator.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_jdbc_iri_generation` | `{base}/{table}/{pk}` 형식 |
| `test_api_stream_iri_generation` | `{base}/{entity}/{id}` 형식 |
| `test_manual_iri_generation` | UUID 기반 IRI |
| `test_iri_url_encoding` | 특수문자 포함 PK 처리 |

### 4.4 RDF Transformer (`test_service_rdf_transformer.py` — 신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_transform_jdbc_row_to_triples` | DB row → RDF Triple 목록 |
| `test_transform_api_event_to_triples` | JSON event → RDF Triple 목록 |
| `test_property_mapping_applied` | PropertyMapping 반영 확인 |
| `test_provenance_triple_added` | prov:generatedAtTime 트리플 생성 |

---

## 5. Phase 3 — MCP 도구 테스트

MCP 도구는 서비스 레이어를 Mock하고 입출력 스키마를 검증.

**파일:** `backend/tests/test_mcp_tools.py` (신규 파일)

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `test_mcp_list_ontologies` | 온톨로지 목록 반환 스키마 |
| `test_mcp_get_ontology_summary` | stats 포함 요약 반환 |
| `test_mcp_search_entities` | kind="all" → Concept + Individual 혼합 결과 |
| `test_mcp_search_entities_kind_concept` | kind="concept" → Concept만 |
| `test_mcp_search_relations` | domain_iri 필터 적용 결과 |
| `test_mcp_get_subgraph` | nodes/edges 구조 확인 |
| `test_mcp_sparql_query_select` | SELECT 결과 → variables + bindings |
| `test_mcp_sparql_query_update_blocked` | UPDATE → 오류 반환 |
| `test_mcp_run_reasoner` | consistent + violations + inferredAxiomsCount |

---

## 6. Phase 4 — 프론트엔드 컴포넌트 테스트

**도구:** Vitest + React Testing Library + MSW (API Mock)

### 6.1 환경 설정

```typescript
// frontend/src/tests/setup.ts
import { server } from './mocks/server'
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

```typescript
// frontend/src/tests/mocks/handlers.ts
// MSW로 /api/v1/* 엔드포인트 Mock
```

### 6.2 공통 컴포넌트

**파일:** `frontend/src/components/shared/__tests__/`

| 컴포넌트 | 테스트 케이스 |
|---------|-------------|
| `IRIBadge` | IRI 표시, 클립보드 복사 버튼 클릭 |
| `SearchInput` | onChange 이벤트, debounce |
| `Pagination` | 페이지 이동 버튼 클릭, 현재 페이지 표시 |
| `LoadingSpinner` | size prop별 렌더링 |

### 6.3 EntitiesPage

**파일:** `frontend/src/pages/ontology/__tests__/EntitiesPage.test.tsx`

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `renders concept tab by default` | "concepts" 탭 활성, Concept 목록 표시 |
| `switches to individual tab` | 탭 전환 → Individual 목록 로드 |
| `search filters results` | 검색어 입력 → API 호출에 search 파라미터 포함 |
| `opens create form` | "New Concept" 클릭 → ConceptForm 표시 |
| `submits create form` | 폼 제출 → POST /concepts 호출 |
| `selects entity shows detail panel` | 행 클릭 → EntityDetailPanel 표시 |
| `edit button opens edit panel` | Edit 버튼 → 사이드바 편집 폼 |
| `submit edit form calls update api` | 편집 저장 → PUT /concepts/{iri} 호출 |

### 6.4 RelationsPage

**파일:** `frontend/src/pages/ontology/__tests__/RelationsPage.test.tsx`

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `renders object properties tab by default` | Object Properties 탭 활성 |
| `switches to data tab` | Data Properties 탭 전환 |
| `search input triggers api call with search param` | 검색 연동 |
| `opens create form` | New Property 클릭 |
| `edit property opens edit panel` | Edit → PropertyForm mode=edit |

### 6.5 SPARQLPage

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `renders editor` | CodeMirror 에디터 마운트 |
| `execute button calls sparql api` | 실행 버튼 → POST /sparql |
| `displays results table` | 결과 바인딩 테이블 표시 |
| `displays error on syntax error` | 400 응답 → 에러 메시지 표시 |

### 6.6 HomePage

| 테스트 케이스 | 검증 항목 |
|--------------|----------|
| `lists ontologies as cards` | OntologyCard 목록 렌더링 |
| `create ontology button opens modal` | 새 온톨로지 생성 폼 |
| `clicking card navigates to ontology` | 카드 클릭 → `/ontologies/{id}/graph` 이동 |

---

## 7. Phase 5 — E2E 테스트

**도구:** Playwright
**환경:** Docker Compose 전체 스택 (backend + frontend + Oxigraph)
**전제조건:** `docker compose up` 후 실행

**파일:** `e2e/` 디렉토리 (신규)

### 7.1 핵심 사용자 시나리오

#### 시나리오 1: 온톨로지 생성 → Entity 추가 → SPARQL 조회

```
1. 홈 접속 → "새 온톨로지" 클릭 → 폼 입력 → 생성
2. /entities 탭 → "New Concept" → Person 개념 생성
3. Individual 탭 → "New Individual" → Alice 생성 (type: Person)
4. /sparql 탭 → SELECT ?p WHERE { ?p rdf:type owl:NamedIndividual } → 결과에 Alice 포함
```

#### 시나리오 2: 온톨로지 Import → 탐색

```
1. /import 탭 → FOAF 표준 온톨로지 Import
2. /entities 탭 → Concept 목록에 foaf:Person, foaf:Agent 등 표시
3. 검색창 → "Person" 입력 → 필터링 결과 확인
```

#### 시나리오 3: Reasoner 실행

```
1. Concept 두 개 생성 → 모순 제약 설정 (disjointWith)
2. Individual을 두 Concept 모두에 할당
3. /reasoner 탭 → 추론 실행
4. violations 목록에 DomainRangeViolation 또는 DisjointViolation 표시 확인
```

#### 시나리오 4: Relation 생성 → 그래프 뷰 확인

```
1. Concept 두 개 생성 (Employee, Department)
2. Object Property "worksFor" 생성 (domain: Employee, range: Department)
3. /graph 탭 → 두 노드와 엣지 확인
```

### 7.2 E2E 실행 명령

```bash
docker compose up -d
npx playwright test e2e/
```

---

## 8. 실행 방법

### 8.1 백엔드 테스트

```bash
cd backend

# 전체 실행
pytest

# 특정 파일만
pytest tests/test_ontologies.py

# 특정 케이스만
pytest tests/test_ontologies.py::test_create_ontology

# 커버리지 포함
pytest --cov=. --cov-report=term-missing

# 빠른 실행 (외부 의존 없음)
pytest -x --tb=short
```

### 8.2 프론트엔드 테스트

```bash
cd frontend

# 전체 실행
npm run test

# Watch 모드
npm run test:watch

# 커버리지
npm run test:coverage
```

### 8.3 E2E 테스트

```bash
# 환경 구동
docker compose up -d

# E2E 실행
npx playwright test

# 헤드리스 해제 (디버깅용)
npx playwright test --headed
```

---

## 9. 커버리지 목표

| 레이어 | 목표 커버리지 | 우선 대상 |
|--------|-------------|----------|
| 서비스 레이어 (OntologyStore 등) | **80% 이상** | sparql_select, insert_triples, delete_graph |
| API 엔드포인트 | **70% 이상** | CRUD 정상 경로 + 주요 에러 케이스 |
| MCP 도구 | **70% 이상** | 입출력 스키마 검증 |
| 프론트엔드 컴포넌트 | **60% 이상** | EntitiesPage, RelationsPage, SPARQLPage |
| E2E | 핵심 시나리오 4개 | 완전 실행 |

---

## 10. 구현 순서

```
[Week 1] Phase 1 — conftest.py 구현 + 온톨로지/Concept/Individual/Property CRUD 테스트
[Week 1] Phase 2 — OntologyStore 단위 테스트 + SearchService 단위 테스트
[Week 2] Phase 1 — Search/SPARQL/Import/Merge/Reasoner/Sources API 테스트
[Week 2] Phase 3 — MCP 도구 테스트
[Week 3] Phase 4 — 프론트엔드 컴포넌트 테스트 (MSW 환경 설정 포함)
[Week 4] Phase 5 — E2E 테스트 (Playwright 설정 + 시나리오 4개)
```

---

*이 문서는 테스트 구현을 진행하면서 계속 업데이트됩니다.*

---

## 11. 통합 테스트 시나리오: HR 도메인 온톨로지

**파일:** `backend/tests/test_integration_hr_ontology.py`
**작성일:** 2026-03-25
**실행 결과:** **18/18 PASSED** (0.63s)

### 11.1 시나리오 개요

HR(인사) 도메인의 온톨로지를 처음부터 끝까지 API로 구축하는 전 과정을 10단계로 검증한다.

```
https://hr.example.org/onto (BASE IRI)
```

### 11.2 단계별 시나리오

| 단계 | 설명 | 엔드포인트 | 기대 결과 |
|------|------|-----------|----------|
| Step 1 | 온톨로지 생성 | POST /ontologies | 201, id/iri/label 반환 |
| Step 2a | Person Concept 생성 | POST /ontologies/{id}/concepts | 201, iri 일치 |
| Step 2b | Employee 생성 (Person 서브클래스) | POST /ontologies/{id}/concepts | 201, super_classes에 Person 포함 |
| Step 2c | Manager 생성 (Employee 서브클래스) | POST /ontologies/{id}/concepts | 201, super_classes에 Employee 포함 |
| Step 2d | Concept 목록 조회 (3개) | GET /ontologies/{id}/concepts | total=3, Person/Employee/Manager 포함 |
| Step 3 | worksFor ObjectProperty 생성 | POST /ontologies/{id}/properties | 201, domain/range/characteristics 반환 |
| Step 4 | age DataProperty 생성 | POST /ontologies/{id}/properties | 201, range에 xsd:integer 포함 |
| Step 5a | Alice Individual 생성 (Manager 타입) | POST /ontologies/{id}/individuals | 201, types에 Manager 포함 |
| Step 5b | Bob Individual 생성 (Employee 타입) | POST /ontologies/{id}/individuals | 201, types에 Employee 포함 |
| Step 5c | Individual 목록 조회 (2개) | GET /ontologies/{id}/individuals | total=2, Alice/Bob 포함 |
| Step 6a | "employ" 키워드 Concept 검색 | GET /search/entities?q=employ&kind=concept | Employee 반환, Person 미반환 |
| Step 6b | kind=all 통합 검색 | GET /search/entities?kind=all | concept + individual 종류 포함 |
| Step 7a | SPARQL SELECT (NamedIndividual 전체) | POST /sparql | Alice/Bob IRI 결과에 포함 |
| Step 7b | SPARQL UPDATE 차단 | POST /sparql (INSERT) | 400 SPARQL_UPDATE_FORBIDDEN |
| Step 8 | 통계 확인 | GET /ontologies/{id} (stats 필드) | concepts=3, individuals=2, object_properties≥1, data_properties≥1 |
| Step 9 | Employee comment 업데이트 | PUT /ontologies/{id}/concepts/{iri} | 200, 변경된 comment 반환 |
| Step 10a | 온톨로지 삭제 | DELETE /ontologies/{id} | 204 → 이후 GET 404 |
| Step 10b | 삭제 후 Concept 소멸 확인 | DELETE → GET /concepts | 온톨로지 404로 Concept 접근 불가 |

### 11.3 테스트 실행 결과

```
$ python -m pytest tests/test_integration_hr_ontology.py -v

tests/test_integration_hr_ontology.py::test_step1_create_ontology                     PASSED
tests/test_integration_hr_ontology.py::test_step2a_create_concept_person              PASSED
tests/test_integration_hr_ontology.py::test_step2b_create_concept_employee_subclass_of_person PASSED
tests/test_integration_hr_ontology.py::test_step2c_create_concept_manager_subclass_of_employee PASSED
tests/test_integration_hr_ontology.py::test_step2d_list_concepts_returns_three        PASSED
tests/test_integration_hr_ontology.py::test_step3_create_object_property              PASSED
tests/test_integration_hr_ontology.py::test_step4_create_data_property                PASSED
tests/test_integration_hr_ontology.py::test_step5a_create_individual_alice_manager    PASSED
tests/test_integration_hr_ontology.py::test_step5b_create_individual_bob_employee     PASSED
tests/test_integration_hr_ontology.py::test_step5c_list_individuals_returns_two       PASSED
tests/test_integration_hr_ontology.py::test_step6_search_entities_by_keyword          PASSED
tests/test_integration_hr_ontology.py::test_step6_search_entities_all_kinds           PASSED
tests/test_integration_hr_ontology.py::test_step7_sparql_select_all_individuals       PASSED
tests/test_integration_hr_ontology.py::test_step7_sparql_update_blocked               PASSED
tests/test_integration_hr_ontology.py::test_step8_ontology_stats                      PASSED
tests/test_integration_hr_ontology.py::test_step9_update_concept_comment              PASSED
tests/test_integration_hr_ontology.py::test_step10_delete_ontology                    PASSED
tests/test_integration_hr_ontology.py::test_step10_delete_also_removes_concepts       PASSED

============================== 18 passed in 0.63s ==============================
```

### 11.4 전체 백엔드 테스트 결과

```
$ python -m pytest --tb=short -q
============================== 103 passed in 2.17s ==============================
```

### 11.5 버그 수정 이력 (통합 테스트 과정에서 발견)

| 버그 ID | 파일 | 내용 | 수정 방법 |
|---------|------|------|----------|
| BUG-006 | `services/ingestion/iri_generator.py` | `urn:` 형식 IRI를 유효하지 않다고 판단 | 정규식 `^[a-zA-Z][a-zA-Z0-9+\-.]*:` 으로 수정 (슬래시 제거) |
| BUG-007 | `services/search_service.py` | `NotImplementedError` 발생 | SPARQL 기반 키워드 검색으로 완전 구현 |
| BUG-008 | `app_mcp/tools.py` | Individual MCP 검색 시 `GRAPH ?g` 절 누락 | Named Graph 전체 탐색으로 수정 |
| BUG-009 | `api/properties.py`, `api/search.py` | `UUID/tbox` IRI 형식 오류 (dc:identifier lookup 없이 직접 UUID 사용) | `_resolve_tbox()` 헬퍼로 UUID→IRI 변환 후 TBox 경로 생성 |
| BUG-010 | `api/individuals.py`, `api/search.py` | Individual SPARQL 쿼리에 `GRAPH ?g` 절 누락으로 조회 결과 0건 | 모든 Individual 쿼리에 `GRAPH ?g {}` 추가 |
| WARNING-001 | `services/ontology_store.py` | `RdfFormat` 미임포트로 Turtle 직렬화 실패 | `pyoxigraph.RdfFormat` 임포트 + `dump()` API 수정 |
| BUG-011 | `services/graph_store.py` | `session.begin_transaction()` 코루틴을 `async with` 직접 사용 → TypeError | `async with await session.begin_transaction() as tx:` 로 수정 |
| BUG-012 | `frontend/src/api/ontologies.ts` | `listOntologies`/`getOntology` 응답에서 `label`→`name`, `iri`→`base_iri` 매핑 누락 | `mapOntology()` 헬퍼 추가 |
| BUG-013 | `frontend/src/api/relations.ts` | `/properties/object`, `/properties/data` 非存在 엔드포인트 호출 | `/properties?kind=object`, `/properties?kind=data` 로 수정 |
| BUG-014 | `frontend/src/api/ontologies.ts` | `createOntology` 요청 시 `name`/`base_iri` 전송 (백엔드는 `label`/`iri` 기대) | 요청 body 필드 매핑 추가 |
| BUG-015 | `backend/api/import_.py` | `tbox_iri = f"{ontology_id}/tbox"` — UUID를 IRI로 사용해 잘못된 Named Graph에 저장 | `_resolve_tbox()` 헬퍼로 올바른 IRI 기반 TBox 경로 사용 |
| BUG-016 | `frontend/src/pages/ontology/ImportPage.tsx` | 단일 `/import` 엔드포인트 호출 (존재하지 않음) | `/import/standard`, `/import/url`, `/import/file` 각각으로 분리 |

### 11.6 E2E 테스트 최종 결과 (2026-03-26)

Docker Compose 전체 스택(`backend + frontend + neo4j + kafka`) 구동 후 실행.

```
$ cd frontend && CI=true E2E_BASE_URL=http://localhost npx playwright test e2e/

Running 11 tests using 1 worker

[1/11]  시나리오 1 › 1-1. 홈에서 새 온톨로지 생성 UI 확인        ✅
[2/11]  시나리오 1 › 1-2. Entities 탭에서 Concept(Person) 추가    ✅
[3/11]  시나리오 1 › 1-3. Individuals 탭에서 Individual(Alice) 추가 ✅
[4/11]  시나리오 1 › 1-4. SPARQL 탭에서 Individual 조회           ✅
[5/11]  시나리오 2 › 2-1. Import 탭에서 FOAF 표준 온톨로지 Import  ✅
[6/11]  시나리오 2 › 2-2. Entities 탭에서 foaf:Person 확인         ✅
[7/11]  시나리오 2 › 2-3. 검색으로 필터링                          ✅
[8/11]  시나리오 3 › 3-1. Reasoner 탭 접근 및 실행                 ✅
[9/11]  시나리오 3 › 3-2. 불일치 violations 표시 확인              ✅
[10/11] 시나리오 4 › 4-1. Relations 탭에서 Object Property 생성    ✅
[11/11] 시나리오 4 › 4-2. Graph 탭에서 노드 렌더링 확인            ✅

11 passed (10.7s)
```

**결과: 11/11 전부 통과** ✅
