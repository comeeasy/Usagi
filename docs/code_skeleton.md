# 코드 스켈레톤 문서: Palantir Foundry 온톨로지 플랫폼

**작성일:** 2026-03-23
**버전:** 1.0
**기반 설계서:** docs/specification.md v1.0

---

## 목차

1. [전체 디렉토리 트리](#1-전체-디렉토리-트리)
2. [인프라 파일](#2-인프라-파일)
3. [Backend 파일 상세](#3-backend-파일-상세)
4. [Frontend 파일 상세](#4-frontend-파일-상세)

---

## 1. 전체 디렉토리 트리

```
/
├── docker-compose.yml              # Docker Compose 전체 서비스 정의 (backend, frontend, neo4j, kafka, nginx)
├── nginx/
│   └── nginx.conf                  # Nginx 리버스 프록시: /api/* → backend:8000, /* → frontend:3000
│
├── backend/
│   ├── Dockerfile                  # Python 3.12 slim 이미지, uvicorn 실행
│   ├── requirements.txt            # 백엔드 의존성 패키지 목록
│   ├── main.py                     # FastAPI + FastMCP 앱 진입점, lifespan으로 worker 시작
│   ├── config.py                   # pydantic BaseSettings로 환경변수 로드
│   │
│   ├── api/
│   │   ├── __init__.py             # 라우터 모음 export
│   │   ├── ontologies.py           # 온톨로지 CRUD 라우터 (/api/v1/ontologies)
│   │   ├── concepts.py             # Concept CRUD 라우터 (/api/v1/ontologies/{id}/concepts)
│   │   ├── individuals.py          # Individual CRUD + Provenance 라우터
│   │   ├── properties.py           # ObjectProperty / DataProperty CRUD 라우터
│   │   ├── search.py               # Entity/Relation 검색 라우터 (키워드 + 벡터)
│   │   ├── subgraph.py             # 서브그래프 쿼리 라우터
│   │   ├── sparql.py               # SPARQL 에디터 엔드포인트 라우터
│   │   ├── import_.py              # 온톨로지 파일/URL Import 라우터
│   │   ├── merge.py                # 온톨로지 Merge 라우터
│   │   ├── reasoner.py             # Reasoner 실행/결과 조회 라우터
│   │   └── sources.py              # Backing Source 관리 + 수동 Sync 라우터
│   │
│   ├── mcp/
│   │   ├── __init__.py             # FastMCP 인스턴스 export
│   │   └── tools.py                # FastMCP 7종 도구 정의
│   │
│   ├── services/
│   │   ├── ontology_store.py       # Oxigraph SPARQL wrapper (읽기/쓰기/Named Graph 관리)
│   │   ├── graph_store.py          # Neo4j Cypher wrapper (연결 풀, CRUD, GDS)
│   │   ├── reasoner_service.py     # owlready2 HermiT 추론 실행 + 결과 직렬화
│   │   ├── merge_service.py        # 온톨로지 Merge 로직 + 충돌 감지
│   │   ├── import_service.py       # rdflib 파싱 + Oxigraph bulk insert
│   │   ├── search_service.py       # 검색 (SPARQL 키워드 + 벡터 검색)
│   │   ├── sync_service.py         # Oxigraph → Neo4j 동기화 실행 로직
│   │   └── ingestion/
│   │       ├── __init__.py         # 수집 파이프라인 모듈 export
│   │       ├── kafka_consumer.py   # Kafka rdf-triples 토픽 Consumer
│   │       ├── kafka_producer.py   # raw-source-events 발행 Producer
│   │       ├── rdf_transformer.py  # 소스 이벤트 → RDF Triple 변환
│   │       ├── iri_generator.py    # 소스 유형별 IRI 생성 전략
│   │       └── r2rml_mapper.py     # R2RML 기반 RDB→RDF 매핑
│   │
│   ├── models/
│   │   ├── __init__.py             # Pydantic 모델 export
│   │   ├── ontology.py             # Ontology, OntologyStats, OntologyCreate, OntologyUpdate
│   │   ├── concept.py              # Concept, ConceptCreate, ConceptUpdate, PropertyRestriction
│   │   ├── individual.py           # Individual, IndividualCreate, ProvenanceRecord, DataPropertyValue
│   │   ├── property.py             # ObjectProperty, DataProperty, PropertyCreate
│   │   ├── source.py               # BackingSource, JDBCConfig, APIConfig, StreamConfig, PropertyMapping
│   │   └── reasoner.py             # ReasonerResult, ReasonerViolation, InferredAxiom, JobResponse
│   │
│   ├── workers/
│   │   ├── sync_worker.py          # Oxigraph→Neo4j 주기 동기화 asyncio 태스크
│   │   └── kafka_worker.py         # Kafka Consumer 상시 실행 asyncio 태스크
│   │
│   └── tests/
│       ├── __init__.py             # 테스트 패키지
│       ├── conftest.py             # pytest fixtures (TestClient, mock stores)
│       ├── test_ontologies.py      # 온톨로지 API 테스트
│       └── test_concepts.py        # Concept API 테스트
│
├── frontend/
│   ├── Dockerfile                  # Node 20 빌드 → Nginx 정적 파일 서빙
│   ├── package.json                # 의존성 및 스크립트
│   ├── tsconfig.json               # TypeScript 컴파일러 설정
│   ├── vite.config.ts              # Vite 빌드 설정 (proxy, alias)
│   ├── tailwind.config.ts          # Tailwind CSS 커스텀 설정
│   ├── index.html                  # SPA 진입점 HTML
│   │
│   └── src/
│       ├── main.tsx                # React DOM 렌더링 진입점
│       ├── App.tsx                 # React Router 라우트 정의
│       │
│       ├── pages/
│       │   ├── HomePage.tsx                    # 온톨로지 목록 + 통계 카드 그리드
│       │   ├── MCPDebugPage.tsx                # MCP 서버 상태 / 도구 목록 디버그 페이지
│       │   └── ontology/
│       │       ├── GraphPage.tsx               # Cytoscape.js 그래프 뷰 페이지
│       │       ├── EntitiesPage.tsx            # Entity(Concept+Individual) 탐색 페이지
│       │       ├── RelationsPage.tsx           # Relation(Property) 탐색 페이지
│       │       ├── SPARQLPage.tsx              # SPARQL 에디터 + 결과 페이지
│       │       ├── ImportPage.tsx              # 온톨로지 Import 위저드 페이지
│       │       ├── MergePage.tsx               # 온톨로지 Merge diff 페이지
│       │       ├── ReasonerPage.tsx            # 정합성 검증 + 추론 결과 페이지
│       │       └── SourcesPage.tsx             # Backing Source 관리 페이지
│       │
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx        # 전체 레이아웃 (사이드바 + 상단바 + 콘텐츠 영역)
│       │   │   ├── Sidebar.tsx         # 좌측 내비게이션 (아이콘 + 레이블)
│       │   │   ├── TopBar.tsx          # 상단 온톨로지 제목 + 브레드크럼 + 검색
│       │   │   └── OntologyTabs.tsx    # 서브 탭 (graph/entities/relations/sparql/...)
│       │   │
│       │   ├── graph/
│       │   │   ├── GraphCanvas.tsx         # Cytoscape.js 래퍼 컴포넌트
│       │   │   ├── GraphControls.tsx       # 레이아웃 선택, 줌, 필터 컨트롤바
│       │   │   ├── GraphLegend.tsx         # 노드/엣지 색상 범례
│       │   │   └── NodeDetailPanel.tsx     # 선택된 노드 상세 우측 패널
│       │   │
│       │   ├── entities/
│       │   │   ├── EntitySearchBar.tsx     # 키워드 + 타입 필터 + 벡터 검색 입력
│       │   │   ├── EntityTable.tsx         # Concept/Individual 목록 테이블
│       │   │   ├── EntityDetailPanel.tsx   # 선택 Entity 상세 슬라이딩 패널
│       │   │   ├── ConceptForm.tsx         # Concept 생성/수정 폼
│       │   │   └── IndividualForm.tsx      # Individual 생성/수정 폼
│       │   │
│       │   ├── relations/
│       │   │   ├── RelationSearchBar.tsx   # Property 검색 입력
│       │   │   ├── RelationTable.tsx       # Property 목록 테이블
│       │   │   ├── RelationDetailPanel.tsx # 선택 Property 상세 패널
│       │   │   └── PropertyForm.tsx        # ObjectProperty/DataProperty 생성/수정 폼
│       │   │
│       │   ├── provenance/
│       │   │   └── ProvenancePanel.tsx     # Individual의 Named Graph 출처 목록
│       │   │
│       │   ├── sparql/
│       │   │   ├── SPARQLEditor.tsx        # CodeMirror + SPARQL 언어팩 에디터
│       │   │   └── SPARQLResultsTable.tsx  # SPARQL SELECT 결과 테이블
│       │   │
│       │   ├── reasoner/
│       │   │   ├── SubgraphSelector.tsx    # 추론 대상 Entity 선택 UI
│       │   │   └── ReasonerResults.tsx     # 위반 / 추론된 사실 목록 표시
│       │   │
│       │   ├── sources/
│       │   │   ├── SourceList.tsx          # Backing Source 카드 목록
│       │   │   ├── SourceConfigForm.tsx    # 소스 유형별 설정 폼 (JDBC/API/Stream)
│       │   │   └── MappingEditor.tsx       # 소스 필드 → Property IRI 매핑 에디터
│       │   │
│       │   └── shared/
│       │       ├── IRIBadge.tsx            # IRI 표시 + 클립보드 복사 버튼
│       │       ├── OntologyCard.tsx        # 홈 화면 온톨로지 통계 카드
│       │       ├── SearchInput.tsx         # 공통 검색 입력 컴포넌트
│       │       ├── Pagination.tsx          # 페이지네이션 컨트롤
│       │       ├── LoadingSpinner.tsx      # 로딩 스피너
│       │       └── ErrorBoundary.tsx       # React ErrorBoundary
│       │
│       ├── hooks/
│       │   ├── useOntology.ts          # 온톨로지 CRUD + 선택 상태 훅
│       │   ├── useEntitySearch.ts      # Entity 검색 훅 (debounce + 캐싱)
│       │   ├── useSPARQL.ts            # SPARQL 쿼리 실행 훅
│       │   ├── useSubgraph.ts          # 서브그래프 쿼리 훅
│       │   └── useReasoner.ts          # 추론 실행 + 폴링 훅
│       │
│       ├── api/
│       │   ├── client.ts               # fetch 기반 base 클라이언트 (에러 핸들링)
│       │   ├── ontologies.ts           # 온톨로지 API 호출 함수
│       │   ├── entities.ts             # Concept/Individual API 호출 함수
│       │   ├── relations.ts            # Property API 호출 함수
│       │   ├── sparql.ts               # SPARQL 실행 API 호출 함수
│       │   ├── reasoner.ts             # Reasoner API 호출 함수
│       │   └── sources.ts              # Backing Source API 호출 함수
│       │
│       └── types/
│           ├── ontology.ts             # Ontology, OntologyStats TypeScript 타입
│           ├── concept.ts              # Concept, PropertyRestriction TypeScript 타입
│           ├── individual.ts           # Individual, ProvenanceRecord TypeScript 타입
│           ├── property.ts             # ObjectProperty, DataProperty TypeScript 타입
│           └── source.ts               # BackingSource, JDBCConfig, APIConfig TypeScript 타입
```

---

## 2. 인프라 파일

### `docker-compose.yml`

**책임:** 전체 서비스 오케스트레이션 (backend, frontend, neo4j, kafka, zookeeper, nginx)

**서비스 구성:**
- `backend`: Python FastAPI + FastMCP, 포트 8000
- `frontend`: React SPA (프로덕션 빌드 시 Nginx 정적 서빙)
- `neo4j`: Community Edition, 포트 7474/7687, 인증 비활성화 (개발환경)
- `zookeeper`: Kafka 의존성, 포트 2181
- `kafka`: Bitnami Kafka, 포트 9092, `raw-source-events`/`rdf-triples`/`sync-commands` 토픽 자동 생성
- `nginx`: 리버스 프록시, 포트 80 (외부 진입점)

**볼륨:** neo4j-data, kafka-data, oxigraph-data (backend에 마운트)

---

### `nginx/nginx.conf`

**책임:** 클라이언트 요청 라우팅

**라우팅 규칙:**
- `/api/` → `http://backend:8000` (proxy_pass)
- `/mcp` → `http://backend:8000/mcp` (SSE 스트리밍 지원: proxy_buffering off)
- `/*` → `http://frontend:3000` (SPA fallback: try_files $uri /index.html)

---

## 3. Backend 파일 상세

### `backend/Dockerfile`

**책임:** Python 3.12 슬림 이미지 기반 백엔드 컨테이너

**빌드 단계:**
1. `python:3.12-slim` 베이스
2. Java 설치 (owlready2 + HermiT JVM 의존성: `default-jre-headless`)
3. `pip install -r requirements.txt`
4. `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`

---

### `backend/requirements.txt`

**책임:** 백엔드 Python 패키지 목록

**패키지 목록:** fastapi, uvicorn, pydantic, pydantic-settings, pyoxigraph, rdflib, owlready2, neo4j, kafka-python, fastmcp, httpx, python-multipart, pytest, pytest-asyncio

---

### `backend/main.py`

**책임:** FastAPI 앱 인스턴스 생성, 라우터 등록, lifespan 관리

**imports:** FastAPI, asyncio, contextlib, 모든 api 라우터, workers, config

**함수/클래스:**

#### `lifespan(app: FastAPI) -> AsyncGenerator`
```
async with asynccontextmanager:
  - OntologyStore 초기화 (Oxigraph Store 연결)
  - GraphStore 초기화 (Neo4j 드라이버 연결)
  - asyncio.create_task(sync_worker()) 시작
  - asyncio.create_task(kafka_worker()) 시작
  - yield
  - 태스크 취소 및 드라이버 close
```

**앱 설정:**
- `app = FastAPI(title="Ontology Platform", lifespan=lifespan)`
- 모든 API 라우터를 `/api/v1` prefix로 include
- FastMCP 인스턴스를 `app.mount("/mcp", mcp_app)` 형태로 마운트
- CORS 미들웨어 추가 (개발: 모든 오리진 허용)

---

### `backend/config.py`

**책임:** 환경변수 기반 앱 설정

**imports:** pydantic_settings.BaseSettings, pydantic.Field

#### `class Settings(BaseSettings)`
```
필드:
  neo4j_uri: str = "bolt://neo4j:7687"
  neo4j_user: str = "neo4j"
  neo4j_password: str = "password"
  kafka_brokers: str = "kafka:9092"
  oxigraph_path: str = "/data/oxigraph"
  sparql_timeout_seconds: int = 30
  sync_interval_seconds: int = 300
  sync_batch_size: int = 1000

  class Config:
    env_file = ".env"

settings = Settings()  # 싱글톤 인스턴스
```

---

### `backend/api/__init__.py`

**책임:** 모든 API 라우터 인스턴스 export

---

### `backend/api/ontologies.py`

**책임:** 온톨로지 CRUD REST 엔드포인트

**imports:** FastAPI APIRouter, HTTPException, 모델, OntologyStore

**라우터:** `router = APIRouter(prefix="/ontologies", tags=["ontologies"])`

#### `GET /ontologies` → `list_ontologies(page, page_size)`
```
구현:
  - OntologyStore.list_ontologies(page, page_size) 호출
  - PaginatedResponse[Ontology] 반환
  - 각 온톨로지에 stats(개념수, 개체수, 속성수) 포함
```

#### `POST /ontologies` → `create_ontology(body: OntologyCreate)`
```
구현:
  - UUID 생성 → owl:Ontology IRI를 Named Graph로 Oxigraph에 저장
  - OWL 메타데이터 트리플 삽입 (rdfs:label, dc:description, owl:versionInfo)
  - 생성된 Ontology 반환
  - 중복 IRI 시 HTTPException 409
```

#### `GET /ontologies/{id}` → `get_ontology(id: str)`
```
구현:
  - Oxigraph에서 해당 온톨로지 메타데이터 SPARQL SELECT
  - SPARQL COUNT로 통계 조회 (concepts, individuals, properties)
  - 404 처리
```

#### `PUT /ontologies/{id}` → `update_ontology(id, body: OntologyUpdate)`
```
구현:
  - SPARQL DELETE/INSERT로 label, description, version 수정
  - 수정된 Ontology 반환
```

#### `DELETE /ontologies/{id}` → `delete_ontology(id: str)`
```
구현:
  - 해당 ontology_id에 속한 모든 Named Graph 삭제
  - Neo4j에서 해당 온톨로지 노드/관계 삭제
  - 204 반환
```

---

### `backend/api/concepts.py`

**책임:** Concept(owl:Class) CRUD

**라우터:** `router = APIRouter(prefix="/ontologies/{ontology_id}/concepts", tags=["concepts"])`

#### `GET /` → `list_concepts(ontology_id, q, super_class, page, page_size)`
```
구현:
  - SPARQL SELECT로 owl:Class 목록 조회
  - q 있을 경우 rdfs:label CONTAINS 필터 추가
  - super_class 있을 경우 rdfs:subClassOf 필터 추가
  - 각 클래스의 individualCount를 COUNT 서브쿼리로 집계
```

#### `POST /` → `create_concept(ontology_id, body: ConceptCreate)`
```
구현:
  - IRI 유효성 검증 (절대 IRI 또는 온톨로지 base IRI 기반 상대 IRI)
  - TBox Named Graph에 owl:Class 트리플 삽입
  - rdfs:subClassOf, rdfs:label, rdfs:comment 트리플 삽입
  - owl:PropertyRestriction 트리플 생성 (restrictions 목록)
  - sync_service에 TBox 변경 이벤트 발행
```

#### `GET /{iri}` → `get_concept(ontology_id, iri: str)`
```
구현:
  - URL 디코딩된 IRI로 SPARQL SELECT
  - superClasses, equivalentClasses, disjointWith, restrictions 모두 조회
  - individualCount 포함
```

#### `PUT /{iri}` → `update_concept(ontology_id, iri, body: ConceptUpdate)`
```
구현:
  - 기존 트리플 DELETE 후 새 트리플 INSERT (SPARQL UPDATE)
  - PropertyRestriction 변경 시 blank node 재생성
  - TBox 변경 이벤트 발행
```

#### `DELETE /{iri}` → `delete_concept(ontology_id, iri)`
```
구현:
  - 해당 클래스의 모든 트리플 삭제
  - 해당 클래스를 참조하는 subClassOf, domain, range도 정리
  - 소속 Individual 처리 정책: type 제거 (Individual 자체는 유지)
```

---

### `backend/api/individuals.py`

**책임:** Individual(owl:NamedIndividual) CRUD + Provenance 조회

#### `GET /` → `list_individuals(ontology_id, type_iri, concept_iri, q, page, page_size)`
#### `POST /` → `create_individual(ontology_id, body: IndividualCreate)`
```
구현:
  - 수동 입력: Named Graph IRI = "{ontology_iri}/manual/{uuid}"
  - rdf:type, DataProperty 값, ObjectProperty 값 트리플 삽입
  - ProvenanceRecord 생성 (sourceType="manual")
```
#### `GET /{iri}` → `get_individual(ontology_id, iri)`
```
구현:
  - 모든 Named Graph에서 해당 IRI의 트리플 수집
  - dataPropertyValues, objectPropertyValues, provenance 조합
```
#### `PUT /{iri}` → `update_individual(ontology_id, iri, body: IndividualUpdate)`
```
구현:
  - conflictPolicy 적용 (user-edit-wins: manual Named Graph에만 기록)
```
#### `DELETE /{iri}` → `delete_individual(ontology_id, iri)`
#### `GET /{iri}/provenance` → `get_provenance(ontology_id, iri)`
```
구현:
  - 모든 Named Graph를 순회하며 prov:generatedAtTime, prov:wasAttributedTo 조회
  - ProvenanceRecord 목록 반환
```

---

### `backend/api/properties.py`

**책임:** ObjectProperty / DataProperty CRUD

#### `GET /` → `list_properties(ontology_id, kind, domain, range, page, page_size)`
```
구현:
  - kind="object": owl:ObjectProperty 조회
  - kind="data": owl:DatatypeProperty 조회
  - kind 없음: 둘 다 조회 후 합산
  - domain/range 필터: rdfs:domain/rdfs:range 필터링
```
#### `POST /` → `create_property(ontology_id, body: PropertyCreate)`
#### `GET /{iri}` → `get_property(ontology_id, iri)`
#### `PUT /{iri}` → `update_property(ontology_id, iri, body)`
#### `DELETE /{iri}` → `delete_property(ontology_id, iri)`

---

### `backend/api/search.py`

**책임:** Entity/Relation 검색 (키워드 + 벡터)

#### `GET /entities` → `search_entities(ontology_id, q, kind, limit)`
```
구현:
  - SearchService.keyword_search_entities(ontology_id, q, kind, limit) 호출
  - rdfs:label CONTAINS 기반 SPARQL 검색
  - 결과: [{ iri, label, kind, types?, matchScore }]
```
#### `GET /relations` → `search_relations(ontology_id, q, domain, range, limit)`
#### `POST /vector` → `vector_search(ontology_id, body: VectorSearchRequest)`
```
구현:
  - SearchService.vector_search(ontology_id, text, k) 호출
  - 텍스트 임베딩 생성 → pgvector/Qdrant 유사도 검색
  - 결과: [{ iri, label, kind, similarity }]
```

---

### `backend/api/subgraph.py`

**책임:** 서브그래프 쿼리 (BFS/DFS N-hop)

#### `POST /subgraph` → `query_subgraph(ontology_id, body: SubgraphRequest)`
```
구현:
  - entity_iris를 시작점으로 depth 만큼 BFS
  - Neo4j Cypher: MATCH path = (n)-[*1..{depth}]-(m) WHERE n.iri IN $iris
  - 결과: { nodes: [...], edges: [...] } (Cytoscape.js 입력 형식)
```

---

### `backend/api/sparql.py`

**책임:** SPARQL SELECT/ASK/CONSTRUCT 실행

#### `POST /sparql` → `execute_sparql(ontology_id, body: SPARQLRequest)`
```
구현:
  - UPDATE 쿼리 감지 시 403 반환 (보안)
  - OntologyStore.sparql_select() 또는 sparql_ask() 호출
  - 결과: { variables: [...], bindings: [...] }
  - SPARQL 문법 오류 시 400 반환 (code: SPARQL_SYNTAX_ERROR)
```

---

### `backend/api/import_.py`

**책임:** OWL/TTL/RDF/JSON-LD 파일 및 URL Import

#### `POST /import/file` → `import_file(ontology_id, file: UploadFile)`
```
구현:
  - 파일 내용을 임시 파일로 저장
  - ImportService.import_from_bytes(ontology_id, bytes, format) 호출
  - 비동기 Job으로 실행 (즉시 jobId 반환)
```
#### `POST /import/url` → `import_url(ontology_id, body: ImportURLRequest)`
```
구현:
  - httpx.AsyncClient로 URL 다운로드
  - Content-Type 기반 포맷 감지
  - ImportService.import_from_bytes() 호출
```
#### `POST /import/standard` → `import_standard(ontology_id, body: ImportStandardRequest)`
```
구현:
  - 사전 정의 온톨로지 URL 매핑 (schema.org, FOAF, DC, SKOS, OWL, RDFS)
  - 해당 URL로 import_url 로직 실행
```

---

### `backend/api/merge.py`

**책임:** 온톨로지 Merge 미리보기 및 실행

#### `POST /merge/preview` → `preview_merge(ontology_id, body)`
```
구현:
  - MergeService.detect_conflicts(target_id, source_id) 호출
  - ConflictList 반환 (type, iri, target값, source값)
```
#### `POST /merge` → `execute_merge(ontology_id, body: MergeRequest)`
```
구현:
  - MergeService.merge(target_id, source_id, resolutions) 호출
  - 충돌 해결 적용 후 TBox Named Graph 갱신
  - JobResponse 반환
```

---

### `backend/api/reasoner.py`

**책임:** OWL 추론 실행 + 결과 조회

#### `POST /reasoner/run` → `run_reasoner(ontology_id, body: ReasonerRunRequest)`
```
구현:
  - asyncio.create_task(ReasonerService.run()) 백그라운드 실행
  - jobId 즉시 반환 (202 Accepted)
```
#### `GET /reasoner/jobs/{job_id}` → `get_reasoner_job(ontology_id, job_id)`
```
구현:
  - 인메모리 job 상태 맵에서 조회 (pending/running/completed/failed)
  - completed면 ReasonerResult 포함하여 반환
```

---

### `backend/api/sources.py`

**책임:** Backing Source CRUD + 수동 Sync 트리거

#### `GET /sources` → `list_sources(ontology_id)`
#### `POST /sources` → `create_source(ontology_id, body: BackingSourceCreate)`
```
구현:
  - BackingSource 메타데이터를 Oxigraph prov Named Graph에 저장
  - 또는 별도 메타데이터 저장소 (간단히 인메모리 딕셔너리로도 가능)
```
#### `GET /sources/{source_id}` → `get_source(ontology_id, source_id)`
#### `PUT /sources/{source_id}` → `update_source(ontology_id, source_id, body)`
#### `DELETE /sources/{source_id}` → `delete_source(ontology_id, source_id)`
#### `POST /sources/{source_id}/sync` → `trigger_sync(ontology_id, source_id)`
```
구현:
  - SyncService.trigger_source_sync(source_id) 호출
  - Kafka Producer로 sync-commands 토픽에 메시지 발행
  - JobResponse 반환
```

---

### `backend/mcp/__init__.py`

**책임:** FastMCP 인스턴스 생성 및 tools 등록

---

### `backend/mcp/tools.py`

**책임:** FastMCP 7종 MCP 도구 정의

**imports:** fastmcp.FastMCP, services

#### `@mcp.tool() list_ontologies()`
```
구현:
  - OntologyStore.list_ontologies() 호출
  - [{ id, iri, label, stats }] 반환
```
#### `@mcp.tool() get_ontology_summary(ontology_id: str)`
#### `@mcp.tool() search_entities(ontology_id, query, kind, limit)`
```
구현:
  - SearchService.keyword_search_entities() 호출
  - 자연어 쿼리를 키워드로 처리 (향후 NL2SPARQL 확장 가능)
```
#### `@mcp.tool() search_relations(ontology_id, query, domain_iri, range_iri, kind, limit)`
#### `@mcp.tool() get_subgraph(ontology_id, entity_iris, depth)`
```
구현:
  - GraphStore.get_subgraph() Neo4j 쿼리
  - { nodes, edges } 반환
```
#### `@mcp.tool() sparql_query(ontology_id, query)`
```
구현:
  - UPDATE 키워드 감지 시 거부 (보안)
  - OntologyStore.sparql_select() 호출
  - { variables, bindings } 반환
```
#### `@mcp.tool() run_reasoner(ontology_id, entity_iris)`
```
구현:
  - ReasonerService.run() 동기 실행 (MCP 컨텍스트에서 await)
  - { consistent, violations, inferredAxiomsCount } 반환
```

---

### `backend/services/ontology_store.py`

**책임:** Oxigraph RDF Triple Store SPARQL 래퍼

#### `class OntologyStore`

##### `__init__(self, path: str)`
```
구현:
  - pyoxigraph.Store(path=path)로 영구 저장소 초기화
  - path가 None이면 인메모리 Store() 생성 (테스트용)
```

##### `async def sparql_select(self, ontology_id: str, query: str) -> list[dict]`
```
구현:
  - pyoxigraph.Store.query(query) 호출
  - 결과 행을 { var: { type, value, datatype? } } 딕셔너리로 변환
    - NamedNode → type="uri", value=str(node)
    - Literal → type="literal", value=str(lit), datatype=str(lit.datatype)
    - BlankNode → type="bnode", value=str(bnode)
  - SparqlSyntaxError 발생 시 커스텀 SparqlSyntaxError 예외 re-raise
  - asyncio.get_event_loop().run_in_executor()로 블로킹 IO 처리
  - 타임아웃: settings.sparql_timeout_seconds
```

##### `async def sparql_update(self, ontology_id: str, update: str) -> None`
```
구현:
  - pyoxigraph.Store.update(update) 호출
  - 쓰기 잠금 주의: asyncio executor에서 실행
```

##### `async def insert_triples(self, graph_iri: str, triples: list[Triple]) -> None`
```
구현:
  - pyoxigraph.NamedNode(graph_iri)로 Named Graph 지정
  - Store.add() 배치 호출 (트랜잭션)
  - Triple = (subject: NamedNode, predicate: NamedNode, object: NamedNode|Literal)
```

##### `async def delete_graph(self, graph_iri: str) -> None`
```
구현:
  - Store.remove_graph(NamedNode(graph_iri)) 호출
```

##### `async def export_turtle(self, ontology_id: str) -> str`
```
구현:
  - CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <tbox_iri> { ?s ?p ?o } } 쿼리
  - rdflib.Graph()로 파싱 후 serialize(format="turtle") 반환
```

##### `async def list_ontologies(self, page: int, page_size: int) -> tuple[list[dict], int]`

##### `async def get_ontology_stats(self, ontology_id: str) -> OntologyStats`

---

### `backend/services/graph_store.py`

**책임:** Neo4j LPG 저장소 Cypher 래퍼

#### `class GraphStore`

##### `__init__(self, uri, user, password)`
```
구현:
  - neo4j.AsyncGraphDatabase.driver(uri, auth=(user, password))
  - 드라이버 연결 풀 크기: max_connection_pool_size=50
```

##### `async def upsert_concept(self, ontology_id, iri, label, super_class_iris)`
```
구현:
  - MERGE (c:Concept {iri: $iri}) SET c.label=$label, c.ontologyId=$ontologyId
  - 각 superClassIri에 대해 MERGE (c)-[:SUBCLASS_OF]->(parent) 관계 생성
```

##### `async def upsert_individual(self, ontology_id, iri, label, type_iris, properties)`
```
구현:
  - MERGE (i:Individual {iri: $iri}) SET i += $properties
  - 각 typeIri에 대해 MERGE (i)-[:TYPE]->(c:Concept {iri: $typeIri})
```

##### `async def upsert_object_property_value(self, subject_iri, property_iri, object_iri)`
```
구현:
  - MATCH (s {iri: $subject}), (o {iri: $object})
  - MERGE (s)-[:RELATION {propertyIri: $propertyIri}]->(o)
```

##### `async def get_subgraph(self, ontology_id, entity_iris, depth) -> dict`
```
구현:
  - MATCH path = (n)-[*1..{depth}]-(m) WHERE n.iri IN $iris AND n.ontologyId=$ontologyId
  - 결과 경로에서 노드와 관계 추출
  - { nodes: [...], edges: [...] } 형식으로 반환
  - 노드 수 제한: 최대 500개 (그래프 렌더링 성능)
```

##### `async def delete_ontology_data(self, ontology_id)`
```
구현:
  - MATCH (n {ontologyId: $ontologyId}) DETACH DELETE n
```

##### `async def close(self)`

---

### `backend/services/reasoner_service.py`

**책임:** owlready2 + HermiT OWL 2 추론 실행

#### `class ReasonerService`

##### `async def run(self, ontology_id: str, entity_iris: list[str] | None) -> str`
```
구현:
  1. OntologyStore.export_turtle(ontology_id) 호출 → Turtle 문자열
  2. entity_iris 있을 경우 해당 서브그래프만 필터링
  3. 임시 파일(tempfile.NamedTemporaryFile) 에 .owl 저장
  4. asyncio executor에서 _run_hermit(tmp_path) 동기 실행
  5. job_store[job_id] 상태 업데이트
  6. job_id 반환
```

##### `def _run_hermit(self, owl_path: str) -> ReasonerResult`
```
구현:
  - owlready2.get_ontology(f"file://{owl_path}").load()
  - with onto: sync_reasoner_hermit(infer_property_values=True, infer_data_property_values=True)
  - onto.inconsistent_classes() → UnsatisfiableClass violations
  - 추론된 트리플: onto.world.sparql("SELECT ...") 또는 인스턴스 속성 비교
  - ReasonerResult 직렬화 반환
  - 실행 시간: time.perf_counter() 측정
```

##### `async def get_result(self, job_id: str) -> ReasonerResult`
```
구현:
  - job_store[job_id] 조회
  - 없으면 404, 실행 중이면 JobResponse(status="running") 반환
```

---

### `backend/services/merge_service.py`

**책임:** 온톨로지 병합 충돌 감지 및 실행

#### `class MergeService`

##### `async def detect_conflicts(self, target_id: str, source_id: str) -> list[ConflictItem]`
```
구현:
  - target TBox에서 모든 Class/Property IRI 목록 조회
  - source TBox에서 동일 IRI 존재 여부 확인
  - 공통 IRI에 대해 rdfs:label, rdfs:domain, rdfs:range, rdfs:subClassOf 비교
  - 값이 다르면 ConflictItem(iri, conflictType, targetValue, sourceValue) 생성
  - 자동 병합 가능 항목(source에만 있는 새 클래스): 별도 목록으로 분류
```

##### `async def merge(self, target_id: str, source_id: str, resolutions: list[ConflictResolution]) -> str`
```
구현:
  - resolutions를 iri → choice 딕셔너리로 인덱싱
  - source TBox 트리플 순회:
    - choice="keep-target": 해당 트리플 스킵
    - choice="keep-source": target TBox에 덮어쓰기
    - choice="merge-both": target에 추가 (list 확장)
  - conflict 해결 없이 자동 병합 가능 항목 직접 삽입
  - 병합 완료 후 TBox Named Graph 저장
  - SyncService.trigger_tbox_sync(target_id) 호출
```

---

### `backend/services/import_service.py`

**책임:** 외부 온톨로지 파일 파싱 및 Oxigraph 적재

#### `class ImportService`

##### `async def import_from_bytes(self, ontology_id: str, data: bytes, mime_type: str) -> str`
```
구현:
  - MIME 타입 → rdflib 포맷 매핑: text/turtle→turtle, application/rdf+xml→xml, application/ld+json→json-ld
  - rdflib.Graph().parse(data=data, format=format)
  - TBox Named Graph에 bulk insert: OntologyStore.insert_triples()
  - owl:Ontology, owl:Class, owl:ObjectProperty, owl:DatatypeProperty 추출
  - 각 Class를 Concept 모델로 변환
  - 트리플 수 카운트 반환 (job 완료 결과용)
```

##### `async def detect_format(self, data: bytes, mime_type: str) -> str`
```
구현:
  - Content-Type 헤더 우선
  - 없으면 파일 내용 첫 512바이트 휴리스틱 감지
  - "@prefix" or "@base" → Turtle
  - "<?xml" + "rdf:" → RDF/XML
  - "{" + "@context" → JSON-LD
```

---

### `backend/services/search_service.py`

**책임:** Entity/Property 키워드 검색 + 벡터 유사도 검색

#### `class SearchService`

##### `async def keyword_search_entities(self, ontology_id, query, kind, limit) -> list[dict]`
```
구현:
  - SPARQL: SELECT ... WHERE { ?iri rdfs:label ?label . FILTER(CONTAINS(LCASE(?label), LCASE($query))) }
  - kind="concept": rdf:type owl:Class 필터
  - kind="individual": rdf:type owl:NamedIndividual 필터
  - matchScore = 1.0 (exact) or 0.8 (contains) — 간단 휴리스틱
```

##### `async def keyword_search_relations(self, ontology_id, query, domain, range_, limit) -> list[dict]`

##### `async def vector_search(self, ontology_id, text: str, k: int) -> list[dict]`
```
구현:
  - 텍스트 임베딩 생성 (sentence-transformers 또는 OpenAI embeddings API)
  - pgvector: SELECT iri, label, 1 - (embedding <=> $vec) AS similarity FROM entity_embeddings ORDER BY similarity DESC LIMIT k
  - 결과: [{ iri, label, kind, similarity }]
  - 임베딩 미구축 시 빈 배열 반환 (graceful degradation)
```

---

### `backend/services/sync_service.py`

**책임:** Oxigraph TBox/ABox → Neo4j LPG 동기화

#### `class SyncService`

##### `async def sync_tbox(self, ontology_id: str) -> None`
```
구현:
  - Oxigraph TBox Named Graph에서 owl:Class 목록 CONSTRUCT
  - 각 Class에 대해 GraphStore.upsert_concept() 호출
  - owl:ObjectProperty, owl:DatatypeProperty에 대해 GraphStore.upsert_property() 호출
  - rdfs:subClassOf 관계 Neo4j에 반영
```

##### `async def sync_abox_batch(self, ontology_id: str, graph_iris: list[str]) -> int`
```
구현:
  - 각 Named Graph에서 owl:NamedIndividual 목록 CONSTRUCT
  - rdf:type, DataProperty 값, ObjectProperty 값 추출
  - GraphStore.upsert_individual() 배치 호출 (UNWIND + MERGE, batch_size=settings.sync_batch_size)
  - 동기화된 트리플 수 반환
```

##### `async def trigger_source_sync(self, source_id: str) -> None`
```
구현:
  - Kafka Producer로 sync-commands 토픽에 { source_id, triggered_at } 메시지 발행
```

##### `async def trigger_tbox_sync(self, ontology_id: str) -> None`
```
구현:
  - 즉시 sync_tbox(ontology_id) 호출 (TBox 변경은 소량이므로 동기 실행)
```

---

### `backend/services/ingestion/__init__.py`

**책임:** 수집 파이프라인 서브모듈 export

---

### `backend/services/ingestion/kafka_consumer.py`

**책임:** `rdf-triples` Kafka 토픽 메시지 소비 + Oxigraph 적재

#### `class RDFTriplesConsumer`

##### `async def start(self) -> None`
```
구현:
  - kafka_python.KafkaConsumer(topic="rdf-triples", bootstrap_servers=settings.kafka_brokers, group_id="ontology-platform")
  - 무한 루프: async for message in consumer
  - 메시지 파싱: { graph_iri, n_triples_content }
  - OntologyStore.insert_triples(graph_iri, parse_ntriples(content)) 호출
  - 오류 시 재시도 3회 후 dead-letter-queue에 발행
  - asyncio.sleep(0)으로 이벤트 루프 양보
```

##### `async def stop(self) -> None`

---

### `backend/services/ingestion/kafka_producer.py`

**책임:** `raw-source-events` 토픽 메시지 발행

#### `class SourceEventProducer`

##### `async def publish_source_event(self, source_id, ontology_id, event_type, records) -> None`
```
구현:
  - kafka_python.KafkaProducer(bootstrap_servers=..., value_serializer=json.dumps)
  - 메시지: { source_id, ontology_id, event_type: "upsert"|"delete", timestamp, records }
  - 파티션 키: source_id (동일 소스의 이벤트 순서 보장)
```

---

### `backend/services/ingestion/rdf_transformer.py`

**책임:** 소스 이벤트 레코드 → RDF Triple 변환

#### `class RDFTransformer`

##### `def transform(self, source: BackingSource, event: SourceEvent) -> list[Triple]`
```
구현:
  1. 각 record에 대해:
     a. IRIGenerator.generate(source.iriTemplate, record) → individual IRI
     b. rdf:type 트리플: (individual, rdf:type, source.conceptIri)
     c. 각 PropertyMapping에 대해:
        - 소스 필드 값 추출
        - DataProperty: (individual, propertyIri, Literal(value, datatype))
        - ObjectProperty: (individual, propertyIri, NamedNode(값이 IRI인 경우))
     d. 메타데이터 트리플: prov:generatedAtTime, prov:wasAttributedTo
  2. Named Graph IRI: f"{source.id}/{event.timestamp}"
  3. event_type="delete"이면 트리플 대신 삭제 명령 생성
```

---

### `backend/services/ingestion/iri_generator.py`

**책임:** 소스 유형별 IRI 생성 전략

#### `class IRIGenerator`

##### `def generate(self, template: str, record: dict) -> str`
```
구현:
  - Python str.format_map() 사용: template.format_map(record)
  - 예: "https://example.org/emp/{emp_id}".format_map({"emp_id": 42}) → "https://example.org/emp/42"
  - 값에 특수 문자 있을 경우 urllib.parse.quote() 적용
  - 생성된 IRI 유효성 검증 (절대 IRI 형식)
```

##### `def generate_named_graph_iri(self, source_id: str, timestamp: str) -> str`
```
구현:
  - f"urn:source:{source_id}:{timestamp}" 형식
  - timestamp는 ISO 8601 (콜론을 하이픈으로 치환)
```

---

### `backend/services/ingestion/r2rml_mapper.py`

**책임:** R2RML(RDB to RDF Mapping Language) 기반 RDB 스키마 → OWL 매핑

#### `class R2RMLMapper`

##### `def parse_mapping(self, r2rml_turtle: str) -> list[TriplesMap]`
```
구현:
  - rdflib로 R2RML 매핑 문서 파싱
  - rr:TriplesMap, rr:subjectMap, rr:predicateObjectMap 추출
  - TriplesMap(subject_template, predicate_object_maps) 리스트 반환
```

##### `async def apply_mapping(self, triples_map: TriplesMap, rows: list[dict]) -> list[Triple]`
```
구현:
  - 각 DB 행에 TriplesMap 적용
  - rr:template 처리: {컬럼명} 치환
  - rr:column 처리: 직접 값 참조
  - rr:constant 처리: 고정값
  - 결과 Triple 목록 반환
```

---

### `backend/models/__init__.py`

**책임:** 모든 Pydantic 모델 re-export

---

### `backend/models/ontology.py`

**책임:** Ontology 관련 Pydantic 모델

**클래스:**
- `OntologyStats(BaseModel)`: concepts, individuals, objectProperties, dataProperties, namedGraphs
- `Ontology(BaseModel)`: id, iri, label, description, version, createdAt, updatedAt, stats
- `OntologyCreate(BaseModel)`: iri, label, description, version
- `OntologyUpdate(BaseModel)`: label, description, version (모두 Optional)
- `PaginatedResponse[T](BaseModel, Generic[T])`: items, total, page, pageSize

---

### `backend/models/concept.py`

**책임:** Concept 관련 Pydantic 모델

**클래스:**
- `PropertyRestriction(BaseModel)`: propertyIri, type (Literal 유니온), value, cardinality
- `Concept(BaseModel)`: iri, ontologyId, label, comment, superClasses, equivalentClasses, disjointWith, restrictions, individualCount
- `ConceptCreate(BaseModel)`: iri, label, comment, superClasses, restrictions
- `ConceptUpdate(BaseModel)`: label, comment, superClasses, equivalentClasses, disjointWith, restrictions (모두 Optional)

---

### `backend/models/individual.py`

**책임:** Individual 관련 Pydantic 모델

**클래스:**
- `DataPropertyValue(BaseModel)`: propertyIri, value, datatype, graphIri
- `ObjectPropertyValue(BaseModel)`: propertyIri, targetIri, graphIri
- `ProvenanceRecord(BaseModel)`: graphIri, sourceId, sourceType, ingestedAt, tripleCount
- `Individual(BaseModel)`: iri, ontologyId, label, types, dataPropertyValues, objectPropertyValues, sameAs, differentFrom, provenance
- `IndividualCreate(BaseModel)`: iri, label, types, dataPropertyValues, objectPropertyValues
- `IndividualUpdate(BaseModel)`: 모두 Optional

---

### `backend/models/property.py`

**책임:** OWL Property 관련 Pydantic 모델

**클래스:**
- `ObjectProperty(BaseModel)`: iri, ontologyId, label, comment, domain, range, superProperties, inverseOf, characteristics
- `DataProperty(BaseModel)`: iri, ontologyId, label, comment, domain, range, superProperties, isFunctional
- `PropertyCreate(BaseModel)`: iri, label, kind (Literal["object", "data"]), domain, range, characteristics, isFunctional
- `PropertyUpdate(BaseModel)`: 모두 Optional

---

### `backend/models/source.py`

**책임:** Backing Source 관련 Pydantic 모델

**클래스:**
- `JDBCConfig(BaseModel)`: jdbcUrl, username, passwordSecret, query, primaryKeyField, pollIntervalSeconds
- `APIConfig(BaseModel)`: url, method, headers, authType, authSecret, responseJsonPath, idField, pollIntervalSeconds
- `StreamConfig(BaseModel)`: kafkaBrokers, kafkaTopic, consumerGroup, idField, deliverySemantics
- `PropertyMapping(BaseModel)`: sourceField, propertyIri, datatype
- `BackingSource(BaseModel)`: id, ontologyId, label, sourceType, conceptIri, iriTemplate, propertyMappings, conflictPolicy, config (Union), status, lastSyncAt
- `BackingSourceCreate(BaseModel)`: label, sourceType, conceptIri, iriTemplate, propertyMappings, conflictPolicy, config

---

### `backend/models/reasoner.py`

**책임:** Reasoner 실행 결과 Pydantic 모델

**클래스:**
- `ReasonerViolation(BaseModel)`: type (UnsatisfiableClass/CardinalityViolation 등), subjectIri, description
- `InferredAxiom(BaseModel)`: subject, predicate, object, inferenceRule
- `ReasonerResult(BaseModel)`: consistent, violations, inferredAxioms, executionMs
- `ReasonerRunRequest(BaseModel)`: subgraphEntityIris (Optional[list[str]])
- `JobResponse(BaseModel)`: jobId, status, createdAt, completedAt, result, error

---

### `backend/workers/sync_worker.py`

**책임:** Oxigraph → Neo4j 주기 동기화 asyncio 백그라운드 태스크

#### `async def sync_worker() -> None`
```
구현:
  - while True:
      await asyncio.sleep(settings.sync_interval_seconds)
      pending_ontology_ids = sync_queue.get_all()
      for ontology_id in pending_ontology_ids:
          await SyncService.sync_abox_batch(ontology_id, get_new_graph_iris(ontology_id))
  - asyncio.CancelledError 처리: 정상 종료
  - 예외 발생 시 logging.exception() + 재시도 (5분 후)
```

---

### `backend/workers/kafka_worker.py`

**책임:** Kafka Consumer 상시 실행 asyncio 태스크

#### `async def kafka_worker() -> None`
```
구현:
  - RDFTriplesConsumer.start() 호출
  - asyncio.CancelledError → consumer.stop() 호출 후 종료
  - 연결 실패 시 지수 백오프 재시도 (1s, 2s, 4s, 8s, max 60s)
```

---

### `backend/tests/conftest.py`

**책임:** pytest 공통 픽스처

**픽스처:**
- `client`: TestClient(app) — httpx.AsyncClient 기반
- `mock_ontology_store`: OntologyStore 인메모리 버전 (pyoxigraph.Store() — no path)
- `mock_graph_store`: GraphStore mock (pytest-mock)
- `sample_ontology`: 테스트용 Ontology 인스턴스
- `sample_concept`: 테스트용 Concept 인스턴스

---

### `backend/tests/test_ontologies.py`

**책임:** 온톨로지 API 엔드포인트 테스트

**테스트 케이스:**
- `test_list_ontologies_empty`: 빈 목록 반환 확인
- `test_create_ontology_success`: 201 + Ontology 반환 확인
- `test_create_ontology_duplicate_iri`: 409 반환 확인
- `test_get_ontology_not_found`: 404 반환 확인
- `test_update_ontology`: 200 + 수정된 데이터 확인
- `test_delete_ontology`: 204 반환 확인

---

### `backend/tests/test_concepts.py`

**책임:** Concept API 엔드포인트 테스트

**테스트 케이스:**
- `test_create_concept_success`
- `test_create_concept_invalid_iri`
- `test_list_concepts_with_filter`
- `test_get_concept_with_restrictions`
- `test_update_concept`
- `test_delete_concept`

---

## 4. Frontend 파일 상세

### `frontend/Dockerfile`

**책임:** Node 20 빌드 + Nginx 정적 파일 서빙

**다단계 빌드:**
1. `node:20-alpine` AS builder: `npm ci && npm run build`
2. `nginx:alpine`: builder의 `/app/dist`를 `/usr/share/nginx/html`에 복사

---

### `frontend/package.json`

**책임:** 의존성 및 npm 스크립트 정의

---

### `frontend/tsconfig.json`

**책임:** TypeScript 컴파일러 설정

---

### `frontend/vite.config.ts`

**책임:** Vite 빌드 도구 설정 (proxy, path alias)

---

### `frontend/tailwind.config.ts`

**책임:** Tailwind CSS 커스텀 색상/폰트 설정

---

### `frontend/index.html`

**책임:** SPA 진입점 HTML

---

### `frontend/src/main.tsx`

**책임:** React 앱 DOM 렌더링

---

### `frontend/src/App.tsx`

**책임:** React Router v7 라우트 정의

**라우트 구조:**
```
/ → AppShell → HomePage
/:ontologyId/graph → GraphPage
/:ontologyId/entities → EntitiesPage
/:ontologyId/relations → RelationsPage
/:ontologyId/sparql → SPARQLPage
/:ontologyId/import → ImportPage
/:ontologyId/merge → MergePage
/:ontologyId/reasoner → ReasonerPage
/:ontologyId/sources → SourcesPage
/mcp-debug → MCPDebugPage
```

---

### Pages

#### `frontend/src/pages/HomePage.tsx`
**책임:** 온톨로지 목록 카드 그리드 + 새 온톨로지 생성 버튼

#### `frontend/src/pages/MCPDebugPage.tsx`
**책임:** MCP 서버 연결 상태 + 7종 도구 목록 + 도구 실행 테스트

#### `frontend/src/pages/ontology/GraphPage.tsx`
**책임:** GraphCanvas + GraphControls + NodeDetailPanel + GraphLegend 조합

#### `frontend/src/pages/ontology/EntitiesPage.tsx`
**책임:** EntitySearchBar + EntityTable + EntityDetailPanel(슬라이딩) + ConceptForm/IndividualForm

#### `frontend/src/pages/ontology/RelationsPage.tsx`
**책임:** RelationSearchBar + RelationTable + RelationDetailPanel + PropertyForm

#### `frontend/src/pages/ontology/SPARQLPage.tsx`
**책임:** SPARQLEditor + 실행 버튼 + SPARQLResultsTable

#### `frontend/src/pages/ontology/ImportPage.tsx`
**책임:** 3-Step 위저드 (소스선택 → 미리보기 → 완료)

#### `frontend/src/pages/ontology/MergePage.tsx`
**책임:** 온톨로지 선택 → 충돌 Diff 뷰 → 충돌 해결 → 병합 실행

#### `frontend/src/pages/ontology/ReasonerPage.tsx`
**책임:** SubgraphSelector + 추론 실행 버튼 + ReasonerResults

#### `frontend/src/pages/ontology/SourcesPage.tsx`
**책임:** SourceList + SourceConfigForm(슬라이딩) + MappingEditor

---

### Layout Components

#### `frontend/src/components/layout/AppShell.tsx`
```
// TODO: 전체 레이아웃 구현
// - Tailwind: flex h-screen bg-[#0D1117]
// - 좌측 Sidebar (w-56, md:w-14, sm:hidden)
// - 우측 flex-col (TopBar h-12 + main flex-1 overflow-auto)
// - Sidebar 접기/펼치기 상태: zustand 전역 상태
// - 반응형: md 이하에서 Sidebar 아이콘만, sm 이하에서 Hamburger
```

#### `frontend/src/components/layout/Sidebar.tsx`
```
// TODO: 내비게이션 사이드바
// - 항목: Home, Graph, Entities, Relations, SPARQL, Import, Merge, Reasoner, Sources, ─, MCP Debug
// - 현재 경로 강조 (NavLink active 클래스)
// - 각 항목: lucide-react 아이콘 + 레이블 (접힌 상태에서는 아이콘만)
// - 하단: 버전 정보
```

#### `frontend/src/components/layout/TopBar.tsx`
```
// TODO: 상단 바
// - 좌측: Sidebar 토글 버튼 (Menu 아이콘) + 현재 온톨로지 IRI 브레드크럼
// - 중앙: 온톨로지 제목
// - 우측: 글로벌 검색 버튼 + 설정 아이콘
```

#### `frontend/src/components/layout/OntologyTabs.tsx`
```
// TODO: 온톨로지 서브 탭
// - 탭 목록: Graph / Entities / Relations / SPARQL / Import / Merge / Reasoner / Sources
// - react-router-dom Link 기반 (/:ontologyId/{tab})
// - 활성 탭 border-bottom + text-primary 강조
```

---

### Graph Components

#### `frontend/src/components/graph/GraphCanvas.tsx`
```
// TODO: Cytoscape.js 그래프 캔버스
// Props: { elements: CytoscapeElements, onNodeSelect: (iri: string) => void, layout: string }
// - useEffect로 cytoscape({ container, elements, style, layout }) 초기화
// - 스타일:
//   - node[kind="concept"]: background-color #2F81F7
//   - node[kind="individual"]: background-color #3FB950
//   - edge[kind="object"]: line-color #A78BFA
//   - edge[kind="data"]: line-color #FB923C
//   - :selected: border-color #F0A93F
// - cy.on("tap", "node", e => onNodeSelect(e.target.data("iri")))
// - 레이아웃: dagre (계층형), fcose (힘 기반), grid, circle
// - cleanup: cy.destroy()
```

#### `frontend/src/components/graph/GraphControls.tsx`
```
// TODO: 그래프 컨트롤 바
// Props: { layout, onLayoutChange, onZoomIn, onZoomOut, onFit, onSearch }
// - 레이아웃 드롭다운: dagre / fcose / grid / circle
// - 줌 버튼, 전체 보기 버튼
// - 엔티티 검색 인풋 (검색 시 해당 노드로 pan/highlight)
```

#### `frontend/src/components/graph/GraphLegend.tsx`
```
// TODO: 색상 범례
// - Concept (파란 원), Individual (초록 원), ObjectProperty (보라 선), DataProperty (주황 선)
// - h-8 고정 하단 바
```

#### `frontend/src/components/graph/NodeDetailPanel.tsx`
```
// TODO: 선택 노드 상세 패널 (우측 w-72 슬라이딩)
// Props: { selectedIri: string | null, ontologyId: string, onClose: () => void }
// - selectedIri 없으면 "노드를 선택하세요" 빈 상태
// - Concept이면 superClasses, restrictions, individualCount 표시
// - Individual이면 dataPropertyValues, objectPropertyValues, ProvenancePanel 포함
// - 편집/삭제 버튼
```

---

### Entity Components

#### `frontend/src/components/entities/EntitySearchBar.tsx`
```
// TODO: 엔티티 검색 바
// Props: { onSearch: (q: string, kind: string) => void }
// - 텍스트 입력 (300ms debounce)
// - 종류 드롭다운: 전체 / Concept / Individual
// - 벡터 검색 토글 버튼
```

#### `frontend/src/components/entities/EntityTable.tsx`
```
// TODO: 엔티티 테이블
// Props: { items: EntityItem[], onSelect: (iri: string) => void, onDelete: (iri: string) => void }
// - 컬럼: 체크박스 / 라벨 / 타입(Concept|Individual) / IRI(IRIBadge) / 액션
// - 행 클릭 시 onSelect 호출
// - 정렬: label ASC/DESC
// - 하단 Pagination 컴포넌트
```

#### `frontend/src/components/entities/EntityDetailPanel.tsx`
```
// TODO: 엔티티 상세 슬라이딩 패널
// - Concept: ConceptForm 표시
// - Individual: IndividualForm + ProvenancePanel 표시
```

#### `frontend/src/components/entities/ConceptForm.tsx`
```
// TODO: Concept 생성/수정 폼
// Props: { concept?: Concept, ontologyId: string, onSave: (data) => void, onCancel: () => void }
// - 필드: IRI (생성시만), label, comment, superClasses (다중 선택), restrictions 목록
// - restrictions: { propertyIri, type, value, cardinality } 동적 추가/삭제
// - React Query mutation으로 API 호출
```

#### `frontend/src/components/entities/IndividualForm.tsx`
```
// TODO: Individual 생성/수정 폼
// - 필드: IRI (생성시만), label, types (다중 Concept 선택)
// - dataPropertyValues: 동적 행 추가 (propertyIri 선택 + 값 입력)
// - objectPropertyValues: 동적 행 추가 (propertyIri 선택 + 대상 IRI 검색)
```

---

### Relation Components

#### `frontend/src/components/relations/RelationSearchBar.tsx`
```
// TODO: Property 검색 바
// - 키워드 입력 + 종류 필터 (Object|Data|전체) + Domain/Range 필터
```

#### `frontend/src/components/relations/RelationTable.tsx`
```
// TODO: Property 테이블
// - 컬럼: 라벨 / 종류 / Domain / Range / 특성(Transitive 등)
```

#### `frontend/src/components/relations/RelationDetailPanel.tsx`
```
// TODO: Property 상세 패널
// - ObjectProperty: domain, range, characteristics, inverseOf, superProperties
// - DataProperty: domain, range (XSD 타입), isFunctional
```

#### `frontend/src/components/relations/PropertyForm.tsx`
```
// TODO: Property 생성/수정 폼
// - kind 선택 (Object/Data) → 조건부 필드 표시
// - Object: characteristics 다중 선택 체크박스
// - Data: range XSD 타입 선택
```

---

### Provenance

#### `frontend/src/components/provenance/ProvenancePanel.tsx`
```
// TODO: Provenance 패널
// Props: { individualIri: string, ontologyId: string }
// - GET /individuals/{iri}/provenance API 호출
// - 각 ProvenanceRecord: sourceType 아이콘 + sourceId + ingestedAt + tripleCount
// - Named Graph IRI (IRIBadge로 표시)
```

---

### SPARQL Components

#### `frontend/src/components/sparql/SPARQLEditor.tsx`
```
// TODO: SPARQL 코드 에디터
// Props: { value: string, onChange: (q: string) => void, onExecute: () => void }
// - @codemirror/view, @codemirror/state, @codemirror/lang-sparql 사용
// - 다크 테마 (Foundry 색상 시스템)
// - Ctrl+Enter로 실행
// - 예제 쿼리 드롭다운 (SELECT, CONSTRUCT, ASK 예시)
```

#### `frontend/src/components/sparql/SPARQLResultsTable.tsx`
```
// TODO: SPARQL 결과 테이블
// Props: { variables: string[], bindings: SPARQLBinding[], executionMs: number }
// - 변수명이 컬럼 헤더
// - 값 타입별 렌더링: uri → IRIBadge, literal → 값+datatype, bnode → 회색 뱃지
// - 결과 없음/오류 상태 표시
```

---

### Reasoner Components

#### `frontend/src/components/reasoner/SubgraphSelector.tsx`
```
// TODO: 추론 대상 엔티티 선택
// Props: { ontologyId: string, selected: string[], onChange: (iris: string[]) => void }
// - 라디오: 전체 온톨로지 / 서브그래프 선택
// - 서브그래프 선택 시: EntitySearchBar로 IRI 검색 → 칩 목록으로 추가
```

#### `frontend/src/components/reasoner/ReasonerResults.tsx`
```
// TODO: 추론 결과 표시
// Props: { result: ReasonerResult | null, isRunning: boolean }
// - isRunning: 로딩 스피너 + "추론 실행 중..." 메시지
// - consistent: boolean 뱃지
// - violations 목록: type별 아이콘 + subjectIri + description
// - inferredAxioms 목록: subject/predicate/object IRI 표시 + inferenceRule
```

---

### Source Components

#### `frontend/src/components/sources/SourceList.tsx`
```
// TODO: Backing Source 카드 목록
// Props: { sources: BackingSource[], onSelect: (id: string) => void, onSync: (id: string) => void }
// - 각 소스: sourceType 아이콘 + label + status 뱃지 + lastSyncAt + 동기화 버튼
// - status 색상: active=green, paused=yellow, error=red
```

#### `frontend/src/components/sources/SourceConfigForm.tsx`
```
// TODO: 소스 설정 폼
// Props: { source?: BackingSource, onSave: (data) => void }
// - sourceType 선택 드롭다운 (jdbc/api-rest/api-stream/manual/owl-file)
// - 타입별 조건부 필드:
//   - jdbc: jdbcUrl, username, passwordSecret, query, primaryKeyField, pollIntervalSeconds
//   - api-rest: url, method, authType, responseJsonPath, idField, pollIntervalSeconds
//   - api-stream: kafkaBrokers, kafkaTopic, consumerGroup, idField, deliverySemantics
```

#### `frontend/src/components/sources/MappingEditor.tsx`
```
// TODO: PropertyMapping 에디터
// Props: { mappings: PropertyMapping[], properties: (ObjectProperty|DataProperty)[], onChange: (mappings) => void }
// - 테이블 형식: sourceField 입력 | propertyIri 선택 드롭다운 | datatype 선택 (Data만)
// - 행 추가/삭제 버튼
```

---

### Shared Components

#### `frontend/src/components/shared/IRIBadge.tsx`
```
// TODO: IRI 표시 뱃지
// Props: { iri: string, short?: boolean }
// - short=true: qname 축약 표시 (prefix:local)
// - 클립보드 복사 버튼 (hover 시 표시)
// - 폰트: JetBrains Mono 12px
```

#### `frontend/src/components/shared/OntologyCard.tsx`
```
// TODO: 홈 화면 온톨로지 카드
// Props: { ontology: Ontology, onClick: () => void }
// - label, IRI (IRIBadge), stats (개념/개체/속성 수)
// - hover: border-color primary 강조
```

#### `frontend/src/components/shared/SearchInput.tsx`
```
// TODO: 공통 검색 입력
// Props: { placeholder, value, onChange, onClear }
// - lucide-react Search 아이콘
// - 값 있을 때 X 클리어 버튼
```

#### `frontend/src/components/shared/Pagination.tsx`
```
// TODO: 페이지네이션
// Props: { page, pageSize, total, onPageChange }
// - 이전/다음 버튼, 페이지 번호 목록 (최대 7개 표시)
// - "총 N건" 텍스트
```

#### `frontend/src/components/shared/LoadingSpinner.tsx`
```
// TODO: 로딩 스피너
// Props: { size?: 'sm' | 'md' | 'lg', className? }
// - Tailwind animate-spin
```

#### `frontend/src/components/shared/ErrorBoundary.tsx`
```
// TODO: React ErrorBoundary
// - getDerivedStateFromError: hasError 상태 설정
// - render: 오류 발생 시 fallback UI (재시도 버튼 포함)
```

---

### Hooks

#### `frontend/src/hooks/useOntology.ts`
```
// TODO: 온톨로지 훅
// - useQuery(["ontologies"], api.ontologies.list) — 목록
// - useMutation(api.ontologies.create) — 생성
// - useMutation(api.ontologies.update) — 수정
// - useMutation(api.ontologies.delete) — 삭제
// - zustand 스토어에 selectedOntologyId 저장
```

#### `frontend/src/hooks/useEntitySearch.ts`
```
// TODO: 엔티티 검색 훅
// - useQuery with debounce (300ms)
// - 키워드 변경 시 자동 재검색
// - 벡터 검색 모드 토글
```

#### `frontend/src/hooks/useSPARQL.ts`
```
// TODO: SPARQL 실행 훅
// - useMutation(api.sparql.execute)
// - 실행 시간 측정 (Date.now() 기반)
// - 오류 파싱: SPARQL_SYNTAX_ERROR 특별 처리
```

#### `frontend/src/hooks/useSubgraph.ts`
```
// TODO: 서브그래프 훅
// - useQuery(["subgraph", ontologyId, entityIris, depth], ...)
// - enabled: entityIris.length > 0
// - 결과를 Cytoscape.js elements 형식으로 변환
```

#### `frontend/src/hooks/useReasoner.ts`
```
// TODO: 추론 훅
// - useMutation(api.reasoner.run) → jobId 획득
// - jobId 있으면 useQuery로 5초 주기 폴링 (refetchInterval)
// - status="completed" 시 폴링 중단
```

---

### API Clients

#### `frontend/src/api/client.ts`
```
// TODO: fetch 기반 API 클라이언트
// - BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1"
// - apiFetch<T>(path, options): Promise<T>
//   - 200-299: JSON 파싱 + 반환
//   - 4xx/5xx: ErrorResponse 파싱 + throw ApiError
// - ApiError 클래스: message, code, status
```

#### `frontend/src/api/ontologies.ts`
```
// TODO:
// list(page, pageSize): GET /ontologies
// create(data): POST /ontologies
// get(id): GET /ontologies/:id
// update(id, data): PUT /ontologies/:id
// delete(id): DELETE /ontologies/:id
```

#### `frontend/src/api/entities.ts`
```
// TODO:
// listConcepts(ontologyId, params): GET /ontologies/:id/concepts
// createConcept(ontologyId, data): POST
// getConcept(ontologyId, iri): GET
// updateConcept(ontologyId, iri, data): PUT
// deleteConcept(ontologyId, iri): DELETE
// listIndividuals / createIndividual / ... (동일 패턴)
// getProvenance(ontologyId, iri): GET /individuals/:iri/provenance
```

#### `frontend/src/api/relations.ts`
```
// TODO:
// listProperties(ontologyId, params): GET /ontologies/:id/properties
// createProperty / getProperty / updateProperty / deleteProperty
```

#### `frontend/src/api/sparql.ts`
```
// TODO:
// execute(ontologyId, query): POST /ontologies/:id/sparql
```

#### `frontend/src/api/reasoner.ts`
```
// TODO:
// run(ontologyId, entityIris): POST /ontologies/:id/reasoner/run
// getJob(ontologyId, jobId): GET /ontologies/:id/reasoner/jobs/:jobId
```

#### `frontend/src/api/sources.ts`
```
// TODO:
// list / create / get / update / delete / triggerSync
```

---

### Types

#### `frontend/src/types/ontology.ts`
- `Ontology`, `OntologyStats`, `OntologyCreate`, `OntologyUpdate`, `PaginatedResponse<T>`, `ErrorResponse`, `JobResponse`

#### `frontend/src/types/concept.ts`
- `PropertyRestriction`, `Concept`, `ConceptCreate`, `ConceptUpdate`

#### `frontend/src/types/individual.ts`
- `DataPropertyValue`, `ObjectPropertyValue`, `ProvenanceRecord`, `Individual`, `IndividualCreate`

#### `frontend/src/types/property.ts`
- `ObjectPropertyCharacteristic`, `ObjectProperty`, `DataProperty`, `XSDDatatype`, `PropertyCreate`

#### `frontend/src/types/source.ts`
- `SourceType`, `BackingSource`, `JDBCConfig`, `APIConfig`, `StreamConfig`, `PropertyMapping`, `BackingSourceCreate`
