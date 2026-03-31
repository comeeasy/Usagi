# 설계서: Palantir Foundry 온톨로지 플랫폼

**작성일:** 2026-03-23
**버전:** 1.0
**기반 기획서:** docs/plan.md v1.2

---

## 목차

1. [전체 시스템 아키텍처](#1-전체-시스템-아키텍처)
2. [컴포넌트 구조도](#2-컴포넌트-구조도)
3. [데이터 구조 (TypeScript 타입 명세)](#3-데이터-구조)
4. [API 엔드포인트 명세](#4-api-엔드포인트-명세)
5. [MCP 도구 명세](#5-mcp-도구-명세)
6. [페이지별 레이아웃 명세](#6-페이지별-레이아웃-명세)
7. [색상 시스템 / 타이포그래피](#7-색상-시스템--타이포그래피)
8. [반응형 브레이크포인트](#8-반응형-브레이크포인트)
9. [백엔드 서비스 내부 설계](#9-백엔드-서비스-내부-설계)
10. [수집 파이프라인 상세 설계](#10-수집-파이프라인-상세-설계)
11. [오픈소스 라이브러리 및 도구 목록](#11-오픈소스-라이브러리-및-도구-목록)

---

## 1. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│  CLIENT LAYER                                                        │
│                                                                      │
│  [Browser (React SPA)]          [AI Agent (MCP Client)]             │
│   - Cytoscape.js 그래프 뷰                                           │
│   - SPARQL 에디터 (CodeMirror)                                       │
│   - Entity / Relation 탐색                                           │
└────────────────┬───────────────────────────────┬────────────────────┘
                 │ REST / WebSocket               │ MCP (SSE/stdio)
┌────────────────▼───────────────────────────────▼────────────────────┐
│  APPLICATION LAYER (FastAPI + FastMCP — 단일 Python 프로세스)        │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐   │
│  │  REST API    │  │  MCP Server  │  │  Background Workers     │   │
│  │  (FastAPI)   │  │  (FastMCP)   │  │  (asyncio tasks)        │   │
│  │              │  │              │  │  - Oxigraph→Neo4j 동기화 │   │
│  │  /api/v1/... │  │  tools: 7종  │  │  - Kafka Consumer       │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────────┘   │
│         └─────────────────┴──────────────────────┘                  │
│                            │                                         │
│  ┌─────────────────────────▼──────────────────────────────────────┐ │
│  │                    SERVICE LAYER                               │ │
│  │  OntologyService │ SearchService │ ReasonerService │           │ │
│  │  IngestionService │ SyncService │ MergeService │              │ │
│  └─────────────────────────┬──────────────────────────────────────┘ │
└────────────────────────────┼────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│  DATA LAYER                                                          │
│                                                                      │
│  ┌──────────────────────┐     ┌─────────────────────────────────┐   │
│  │  Oxigraph            │     │  Neo4j                          │   │
│  │  (RDF Triple Store)  │────▶│  (LPG — 탐색 전용)             │   │
│  │  - Source of truth   │sync │  - Cypher 탐색                  │   │
│  │  - SPARQL 1.1        │     │  - 그래프 시각화 데이터         │   │
│  │  - Named Graph       │     │  - MCP 질의                     │   │
│  │  - OWL 추론 (R/W)    │     │  - GDS 알고리즘                 │   │
│  └──────────────────────┘     └─────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────┐     ┌─────────────────────────────────┐   │
│  │  Kafka               │     │  pgvector / Qdrant (선택)       │   │
│  │  (메시지 큐)          │     │  (Embedding 기반 검색)          │   │
│  │  - raw-source-events │     │                                 │   │
│  │  - rdf-triples       │     │                                 │   │
│  └──────────────────────┘     └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  EXTERNAL DATA SOURCES (수집 대상)                                   │
│                                                                      │
│  [RDB / JDBC]  [REST API Stream]  [OWL 파일]  [수동 Triple 입력]    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 컴포넌트 구조도

### 2.1 Backend 디렉토리 구조

```
backend/
├── main.py                    # FastAPI + FastMCP 앱 진입점
├── config.py                  # 환경변수, 설정 로드
│
├── api/                       # FastAPI 라우터 (HTTP 계층)
│   ├── __init__.py
│   ├── ontologies.py          # 온톨로지 CRUD
│   ├── concepts.py            # Concept CRUD
│   ├── individuals.py         # Individual CRUD + Provenance
│   ├── properties.py          # ObjectProperty / DataProperty CRUD
│   ├── search.py              # Entity/Relation 검색 (키워드 + 벡터)
│   ├── subgraph.py            # 서브그래프 쿼리
│   ├── sparql.py              # SPARQL 에디터 엔드포인트
│   ├── import_.py             # 온톨로지 파일 / URL Import
│   ├── merge.py               # 온톨로지 Merge
│   ├── reasoner.py            # Reasoner 실행 / 결과 조회
│   └── sources.py             # Backing Source 관리 + 수동 Sync
│
├── mcp/                       # FastMCP 서버
│   ├── __init__.py
│   └── tools.py               # MCP 도구 7종 정의
│
├── services/                  # 비즈니스 로직
│   ├── ontology_store.py      # Oxigraph SPARQL wrapper (읽기/쓰기)
│   ├── graph_store.py         # Neo4j Cypher wrapper
│   ├── reasoner_service.py    # owlready2 HermiT 추론 실행
│   ├── merge_service.py       # 온톨로지 Merge 로직 + 충돌 감지
│   ├── import_service.py      # rdflib 파싱 + Oxigraph bulk insert
│   ├── search_service.py      # 검색 (SPARQL + 벡터 검색)
│   ├── sync_service.py        # Oxigraph → Neo4j 동기화 (배경 태스크)
│   └── ingestion/
│       ├── __init__.py
│       ├── kafka_consumer.py  # Kafka rdf-triples 토픽 Consumer
│       ├── kafka_producer.py  # raw-source-events 발행
│       ├── rdf_transformer.py # 소스 이벤트 → RDF Triple 변환
│       ├── iri_generator.py   # 소스 유형별 IRI 생성 전략
│       └── r2rml_mapper.py    # R2RML 기반 RDB→RDF 매핑
│
├── models/                    # Pydantic 요청/응답 모델
│   ├── ontology.py
│   ├── concept.py
│   ├── individual.py
│   ├── property.py
│   ├── source.py
│   └── reasoner.py
│
└── workers/                   # asyncio 백그라운드 태스크
    ├── sync_worker.py         # Oxigraph→Neo4j 주기 동기화
    └── kafka_worker.py        # Kafka Consumer 상시 실행
```

### 2.2 Frontend 컴포넌트 트리

```
src/
├── main.tsx
├── App.tsx                     # 라우터 루트
│
├── pages/
│   ├── HomePage.tsx            # 온톨로지 목록 + 통계
│   ├── ontology/
│   │   ├── GraphPage.tsx       # Cytoscape.js 그래프 뷰
│   │   ├── EntitiesPage.tsx    # Entity(Concept+Individual) 탐색
│   │   ├── RelationsPage.tsx   # Relation 탐색
│   │   ├── SPARQLPage.tsx      # SPARQL 에디터
│   │   ├── ImportPage.tsx      # 온톨로지 Import 위저드
│   │   ├── MergePage.tsx       # 온톨로지 Merge
│   │   ├── ReasonerPage.tsx    # 정합성 검증
│   │   └── SourcesPage.tsx     # Backing Source 관리
│   └── MCPDebugPage.tsx        # MCP 서버 상태 / 도구 목록
│
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx        # 전체 레이아웃 (사이드바 + 메인)
│   │   ├── Sidebar.tsx         # 좌측 내비게이션
│   │   ├── TopBar.tsx          # 상단 온톨로지 제목 + 브레드크럼
│   │   └── OntologyTabs.tsx    # 서브 탭 (graph/entities/relations/...)
│   │
│   ├── graph/
│   │   ├── GraphCanvas.tsx     # Cytoscape.js 래퍼
│   │   ├── GraphControls.tsx   # 레이아웃 선택, 줌, 필터
│   │   ├── GraphLegend.tsx     # 노드/엣지 색상 범례
│   │   └── NodeDetailPanel.tsx # 선택된 노드 상세 (우측 패널)
│   │
│   ├── entities/
│   │   ├── EntitySearchBar.tsx # 키워드 + 타입 필터 + 벡터 검색
│   │   ├── EntityTable.tsx     # Concept/Individual 목록 테이블
│   │   ├── EntityDetailPanel.tsx # 선택 Entity 상세
│   │   ├── ConceptForm.tsx     # Concept 생성/수정 폼
│   │   └── IndividualForm.tsx  # Individual 생성/수정 폼
│   │
│   ├── relations/
│   │   ├── RelationSearchBar.tsx
│   │   ├── RelationTable.tsx
│   │   ├── RelationDetailPanel.tsx
│   │   └── PropertyForm.tsx    # ObjectProperty/DataProperty 폼
│   │
│   ├── provenance/
│   │   └── ProvenancePanel.tsx # Individual의 소스 출처 목록
│   │
│   ├── sparql/
│   │   ├── SPARQLEditor.tsx    # CodeMirror + SPARQL 언어팩
│   │   └── SPARQLResultsTable.tsx
│   │
│   ├── reasoner/
│   │   ├── SubgraphSelector.tsx # 추론 대상 Entity 선택
│   │   └── ReasonerResults.tsx  # 위반 / 추론된 사실 목록
│   │
│   ├── sources/
│   │   ├── SourceList.tsx
│   │   ├── SourceConfigForm.tsx  # 소스 유형별 설정 폼
│   │   └── MappingEditor.tsx     # 소스 필드 → Property IRI 매핑
│   │
│   └── shared/
│       ├── IRIBadge.tsx          # IRI 표시 + 복사 버튼
│       ├── OntologyCard.tsx      # 홈 화면 온톨로지 카드
│       ├── SearchInput.tsx
│       ├── Pagination.tsx
│       ├── LoadingSpinner.tsx
│       └── ErrorBoundary.tsx
│
├── hooks/
│   ├── useOntology.ts
│   ├── useEntitySearch.ts
│   ├── useSPARQL.ts
│   ├── useSubgraph.ts
│   └── useReasoner.ts
│
├── api/                        # API 클라이언트 (fetch wrapper)
│   ├── client.ts               # base URL, 에러 핸들링
│   ├── ontologies.ts
│   ├── entities.ts
│   ├── relations.ts
│   ├── sparql.ts
│   ├── reasoner.ts
│   └── sources.ts
│
└── types/                      # TypeScript 타입 (§3 참조)
    ├── ontology.ts
    ├── concept.ts
    ├── individual.ts
    ├── property.ts
    └── source.ts
```

---

## 3. 데이터 구조

### 3.1 핵심 도메인 타입

```typescript
// ── 온톨로지 ──────────────────────────────────────────────────────
interface Ontology {
  id: string;               // 내부 UUID
  iri: string;              // owl:Ontology IRI (예: "https://example.org/hr")
  label: string;
  description?: string;
  version?: string;
  createdAt: string;        // ISO 8601
  updatedAt: string;
  stats: OntologyStats;
}

interface OntologyStats {
  concepts: number;
  individuals: number;
  objectProperties: number;
  dataProperties: number;
  namedGraphs: number;
}

// ── Concept (owl:Class) ──────────────────────────────────────────
interface Concept {
  iri: string;
  ontologyId: string;
  label: string;
  comment?: string;
  superClasses: string[];         // rdfs:subClassOf 대상 IRI 목록
  equivalentClasses: string[];    // owl:equivalentClass
  disjointWith: string[];         // owl:disjointWith
  restrictions: PropertyRestriction[];
  individualCount: number;        // 인스턴스 수 (캐시)
}

interface PropertyRestriction {
  propertyIri: string;
  type: 'someValuesFrom' | 'allValuesFrom' | 'hasValue'
      | 'minCardinality' | 'maxCardinality' | 'exactCardinality';
  value: string;   // 클래스 IRI 또는 리터럴 값
  cardinality?: number;
}

// ── Individual (owl:NamedIndividual) ─────────────────────────────
interface Individual {
  iri: string;
  ontologyId: string;
  label?: string;
  types: string[];                // rdf:type 대상 Concept IRI 목록
  dataPropertyValues: DataPropertyValue[];
  objectPropertyValues: ObjectPropertyValue[];
  sameAs: string[];               // owl:sameAs
  differentFrom: string[];        // owl:differentFrom
  provenance: ProvenanceRecord[]; // Named Graph별 출처
}

interface DataPropertyValue {
  propertyIri: string;
  value: string;
  datatype: string;  // xsd:string, xsd:integer, xsd:dateTime 등
  graphIri: string;  // 출처 Named Graph
}

interface ObjectPropertyValue {
  propertyIri: string;
  targetIri: string;
  graphIri: string;
}

interface ProvenanceRecord {
  graphIri: string;     // Named Graph IRI
  sourceId: string;     // BackingSource.id
  sourceType: SourceType;
  ingestedAt: string;   // ISO 8601
  tripleCount: number;
}

// ── Object Property (owl:ObjectProperty) ─────────────────────────
interface ObjectProperty {
  iri: string;
  ontologyId: string;
  label: string;
  comment?: string;
  domain: string[];            // Concept IRI 목록
  range: string[];             // Concept IRI 목록
  superProperties: string[];   // rdfs:subPropertyOf
  inverseOf?: string;          // owl:inverseOf
  characteristics: ObjectPropertyCharacteristic[];
}

type ObjectPropertyCharacteristic =
  | 'Functional'
  | 'InverseFunctional'
  | 'Transitive'
  | 'Symmetric'
  | 'Asymmetric'
  | 'Reflexive'
  | 'Irreflexive';

// ── Data Property (owl:DatatypeProperty) ─────────────────────────
interface DataProperty {
  iri: string;
  ontologyId: string;
  label: string;
  comment?: string;
  domain: string[];            // Concept IRI 목록
  range: XSDDatatype[];        // xsd:* 타입 목록
  superProperties: string[];
  isFunctional: boolean;
}

type XSDDatatype =
  | 'xsd:string' | 'xsd:integer' | 'xsd:decimal' | 'xsd:float'
  | 'xsd:double' | 'xsd:boolean' | 'xsd:date' | 'xsd:dateTime'
  | 'xsd:anyURI' | 'xsd:langString';

// ── Backing Source ────────────────────────────────────────────────
type SourceType = 'jdbc' | 'api-rest' | 'api-stream' | 'manual' | 'owl-file' | 'csv-file';

interface BackingSource {
  id: string;
  ontologyId: string;
  label: string;
  sourceType: SourceType;
  conceptIri: string;         // 이 소스가 채우는 Concept IRI
  iriTemplate: string;        // IRI 생성 템플릿: "https://ex.org/emp/{emp_id}"
  propertyMappings: PropertyMapping[];
  conflictPolicy: 'user-edit-wins' | 'latest-wins';
  config: JDBCConfig | APIConfig | StreamConfig | Record<string, never>;
  status: 'active' | 'paused' | 'error';
  lastSyncAt?: string;
}

interface PropertyMapping {
  sourceField: string;        // 소스의 컬럼/필드 이름
  propertyIri: string;        // 대상 OWL Property IRI
  datatype?: XSDDatatype;     // DataProperty인 경우
}

interface JDBCConfig {
  jdbcUrl: string;
  username: string;
  passwordSecret: string;     // 시크릿 참조 키
  query: string;              // SELECT 쿼리 (PK 컬럼 포함 필수)
  primaryKeyField: string;
  pollIntervalSeconds: number;
}

interface APIConfig {
  url: string;
  method: 'GET' | 'POST';
  headers?: Record<string, string>;
  authType: 'none' | 'bearer' | 'basic' | 'apikey';
  authSecret?: string;
  responseJsonPath: string;   // 배열을 가리키는 JSONPath
  idField: string;
  pollIntervalSeconds: number;
}

interface StreamConfig {
  kafkaBrokers: string[];
  kafkaTopic: string;
  consumerGroup: string;
  idField: string;
  deliverySemantics: 'exactly-once' | 'at-least-once';
}

interface CSVConfig {
  fileName: string;           // 서버 저장 파일명 (업로드 후 설정)
  delimiter: ',' | ';' | '\t' | '|';
  hasHeader: boolean;         // 첫 행이 헤더인지
  primaryKeyField: string;    // IRI 생성에 쓸 PK 컬럼명 (iriTemplate의 {key}에 대응)
  encoding: 'utf-8' | 'utf-16' | 'latin-1';
  skipRows?: number;          // 헤더 위 건너뛸 행 수 (기본 0)
}
```

### 3.2 API 요청/응답 래퍼

```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

interface ErrorResponse {
  code: string;       // "CONCEPT_NOT_FOUND", "SPARQL_SYNTAX_ERROR" 등
  message: string;
  detail?: unknown;
}

interface JobResponse {
  jobId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
  result?: unknown;
  error?: string;
}
```

---

## 4. API 엔드포인트 명세

**Base URL:** `/api/v1`
**Content-Type:** `application/json` (파일 업로드 제외)
**인증:** 1차 버전에서는 미구현 (추후 Bearer Token)

### 4.1 온톨로지

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/ontologies` | 온톨로지 목록 (페이지네이션) |
| `POST` | `/ontologies` | 새 온톨로지 생성 |
| `GET` | `/ontologies/{id}` | 온톨로지 상세 + 통계 |
| `PUT` | `/ontologies/{id}` | 메타데이터 수정 (label, description, version) |
| `DELETE` | `/ontologies/{id}` | 온톨로지 + 소속 모든 데이터 삭제 |

### 4.2 Concept

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/ontologies/{id}/concepts` | Concept 목록 (`?q=`, `?superClass=`, `?page=`, `?pageSize=`) |
| `POST` | `/ontologies/{id}/concepts` | Concept 생성 |
| `GET` | `/ontologies/{id}/concepts/{iri}` | Concept 상세 (IRI는 URL 인코딩) |
| `PUT` | `/ontologies/{id}/concepts/{iri}` | Concept 수정 |
| `DELETE` | `/ontologies/{id}/concepts/{iri}` | Concept 삭제 |

### 4.3 Individual

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/ontologies/{id}/individuals` | Individual 목록 (`?type=`, `?conceptIri=`, `?q=`) |
| `POST` | `/ontologies/{id}/individuals` | Individual 생성 (수동 입력) |
| `GET` | `/ontologies/{id}/individuals/{iri}` | Individual 상세 + 모든 Property 값 |
| `PUT` | `/ontologies/{id}/individuals/{iri}` | Individual 수정 |
| `DELETE` | `/ontologies/{id}/individuals/{iri}` | Individual 삭제 |
| `GET` | `/ontologies/{id}/individuals/{iri}/provenance` | Provenance 기록 목록 |

### 4.4 Property

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/ontologies/{id}/properties` | Property 목록 (`?kind=object\|data`, `?domain=`, `?range=`) |
| `POST` | `/ontologies/{id}/properties` | Property 생성 |
| `GET` | `/ontologies/{id}/properties/{iri}` | Property 상세 |
| `PUT` | `/ontologies/{id}/properties/{iri}` | Property 수정 |
| `DELETE` | `/ontologies/{id}/properties/{iri}` | Property 삭제 |

### 4.5 검색

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/ontologies/{id}/search/entities` | 키워드 기반 Entity 검색 (`?q=`, `?kind=concept\|individual`, `?limit=20`) |
| `GET` | `/ontologies/{id}/search/relations` | 키워드 기반 Property 검색 (`?q=`, `?domain=`, `?range=`) |
| `POST` | `/ontologies/{id}/search/vector` | 임베딩 기반 유사 Entity 검색 (body: `{ text: string, k: int }`) |

### 4.6 서브그래프

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/ontologies/{id}/subgraph` | 서브그래프 쿼리 (body: `{ entityIris: string[], depth: 1-5 }`) → Node/Edge 목록 반환 |

### 4.7 SPARQL

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/ontologies/{id}/sparql` | SPARQL SELECT / ASK / CONSTRUCT 실행 (body: `{ query: string }`) |

### 4.8 Import

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/ontologies/{id}/import/file` | OWL/TTL/RDF/JSON-LD 파일 업로드 (multipart/form-data) |
| `POST` | `/ontologies/{id}/import/url` | URL에서 온톨로지 가져오기 (body: `{ url: string }`) |
| `POST` | `/ontologies/{id}/import/standard` | 사전 등록 온톨로지 (body: `{ name: 'schema.org'\|'foaf'\|'dc'\|'skos'\|'owl'\|'rdfs' }`) |

### 4.9 Merge

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/ontologies/{id}/merge/preview` | 병합 충돌 미리보기 (body: `{ sourceOntologyId: string }`) |
| `POST` | `/ontologies/{id}/merge` | 실제 병합 실행 (body: `{ sourceOntologyId: string, resolutions: ConflictResolution[] }`) |

```typescript
interface ConflictResolution {
  iri: string;
  conflictType: 'domain' | 'range' | 'label' | 'superClass';
  choice: 'keep-target' | 'keep-source' | 'merge-both';
}
```

### 4.10 Reasoner

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/ontologies/{id}/reasoner/run` | 추론 실행 (body: `{ subgraphEntityIris?: string[] }`) → `{ jobId }` 즉시 반환 |
| `GET` | `/ontologies/{id}/reasoner/jobs/{jobId}` | 추론 작업 상태 + 결과 조회 |

```typescript
interface ReasonerResult {
  consistent: boolean;
  violations: ReasonerViolation[];
  inferredAxioms: InferredAxiom[];
  executionMs: number;
}

interface ReasonerViolation {
  type: 'UnsatisfiableClass' | 'CardinalityViolation' | 'DisjointViolation' | 'DomainRangeViolation';
  subjectIri: string;
  description: string;
}

interface InferredAxiom {
  subject: string;
  predicate: string;
  object: string;
  inferenceRule: string;
}
```

### 4.11 Backing Sources

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/ontologies/{id}/sources` | Backing Source 목록 |
| `POST` | `/ontologies/{id}/sources` | 새 Backing Source 등록 |
| `GET` | `/ontologies/{id}/sources/{sourceId}` | Source 상세 + 마지막 동기화 상태 |
| `PUT` | `/ontologies/{id}/sources/{sourceId}` | Source 설정 수정 |
| `DELETE` | `/ontologies/{id}/sources/{sourceId}` | Source 삭제 (Triple은 유지, Named Graph 보존) |
| `POST` | `/ontologies/{id}/sources/{sourceId}/sync` | 수동 즉시 동기화 트리거 |
| `POST` | `/ontologies/{id}/sources/{sourceId}/upload` | CSV 파일 업로드 (multipart/form-data, `file` 필드) — 응답: `{ fileUrl, rowCount, headers }` |
| `GET` | `/static/uploads/{filename}` | Neo4j LOAD CSV가 접근하는 파일 서빙 엔드포인트 (내부 전용) |

---

## 5. MCP 도구 명세

**전송 방식:** SSE (Server-Sent Events) — `GET /mcp`
**FastMCP 버전:** 2.x

```python
# 각 도구의 입력/출력 스키마

# 1. list_ontologies
Input:  {}
Output: [{ id, iri, label, stats }]

# 2. get_ontology_summary
Input:  { ontology_id: str }
Output: { iri, label, stats: { concepts, individuals, objectProperties, dataProperties } }

# 3. search_entities
Input:  {
  ontology_id: str,
  query: str,                        # 키워드 또는 자연어
  kind: "concept" | "individual" | "all",  # 기본값: "all"
  limit: int = 10
}
Output: [{ iri, label, kind, types?, matchScore }]

# 4. search_relations
Input:  {
  ontology_id: str,
  query?: str,
  domain_iri?: str,
  range_iri?: str,
  kind: "object" | "data" | "all",
  limit: int = 10
}
Output: [{ iri, label, kind, domain, range, characteristics }]

# 5. get_subgraph
Input:  {
  ontology_id: str,
  entity_iris: list[str],  # 중심 Entity IRI 목록
  depth: int = 2           # 1-5
}
Output: {
  nodes: [{ iri, label, kind, types }],
  edges: [{ source, target, propertyIri, propertyLabel, kind }]
}

# 6. sparql_query
Input:  {
  ontology_id: str,
  query: str    # SPARQL SELECT 또는 ASK만 허용 (UPDATE 차단)
}
Output: {
  variables: list[str],
  bindings: list[dict]   # 각 행: { var: { type, value, datatype? } }
}

# 7. run_reasoner
Input:  {
  ontology_id: str,
  entity_iris?: list[str]  # 없으면 전체 온톨로지
}
Output: {
  consistent: bool,
  violations: [{ type, subjectIri, description }],
  inferredAxiomsCount: int
}
```

---

## 6. 페이지별 레이아웃 명세

모든 페이지는 `AppShell` 안에서 렌더링된다.

### 6.0 AppShell 공통 구조

```
┌──────────────────────────────────────────────────────────┐
│  TOPBAR (h-12)                                           │
│  [≡ Logo]  온톨로지 제목 > 현재 페이지   [검색] [설정]   │
├──────────┬───────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT                                 │
│ (w-56)   │                                               │
│          │                                               │
│ - 홈     │                                               │
│ - Graph  │                                               │
│ - Entity │                                               │
│ - Relation│                                              │
│ - SPARQL │                                               │
│ - Import │                                               │
│ - Merge  │                                               │
│ - Reasoner│                                              │
│ - Sources│                                               │
│ ─────── │                                               │
│ - MCP   │                                               │
└──────────┴───────────────────────────────────────────────┘
```

### 6.1 홈 (/)

```
┌──────────────────────────────────────────────────────┐
│  TOPBAR                                              │
├──────────────────────────────────────────────────────┤
│                                                      │
│  [+ 새 온톨로지]   [🔍 검색창 ________________]        │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │온톨로지  │ │온톨로지  │ │온톨로지  │             │
│  │카드      │ │카드      │ │카드      │  ...        │
│  │label     │ │          │ │          │             │
│  │■ 42 개념 │ │          │ │          │             │
│  │● 1.2K 개체│ │          │ │          │             │
│  │⟷ 18 속성 │ │          │ │          │             │
│  └──────────┘ └──────────┘ └──────────┘             │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 6.2 그래프 뷰 (/:id/graph)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├─────────────────────────────────────────────────────────┤
│ [레이아웃▼] [필터▼] [줌+] [줌-] [전체보기] [검색...]   │  ← GraphControls (h-10)
├──────────────────────────────────────┬──────────────────┤
│                                      │  DETAIL PANEL    │
│                                      │  (w-72, 접기가능)│
│   CYTOSCAPE.JS CANVAS                │                  │
│   (flex-1)                           │  선택 노드 없음  │
│                                      │  시 빈 상태 표시 │
│   노드: 파란원(Concept)               │                  │
│         초록원(Individual)            │  노드 선택 시:   │
│   엣지: 보라(ObjectProperty)          │  - IRI          │
│         주황(DataProperty)            │  - 타입          │
│                                      │  - 속성 목록     │
│                                      │  - Provenance    │
│                                      │  - [편집] [삭제] │
├──────────────────────────────────────┴──────────────────┤
│  GraphLegend (h-8): ■ Concept  ● Individual  ─ ObjProp  DataProp │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Entity 탐색 (/:id/entities)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├────────────────────────────────────────────────────────┤
│  [🔍 검색 ___________________] [개념▼] [개체▼] [+ 추가] │  ← 검색 바 (h-12)
├──────────────────────────────┬─────────────────────────┤
│  ENTITY TABLE (flex-1)       │  DETAIL PANEL (w-96)    │
│                              │                         │
│  ☐  라벨      타입    IRI    │  ConceptForm 또는       │
│  ☐  Alice  Individual  ex:.. │  IndividualForm         │
│  ☐  Person  Concept   ex:.. │  (슬라이딩 패널)        │
│  ☐  ...                      │                         │
│                              │  선택 항목의            │
│  [< 1 2 3 >]  총 1,234건     │  상세 정보 + 편집 폼    │
└──────────────────────────────┴─────────────────────────┘
```

### 6.4 Relation 탐색 (/:id/relations)

Entity 탐색과 동일한 레이아웃. 테이블 컬럼: 라벨 / 종류(Object|Data) / Domain / Range / 특성

### 6.5 SPARQL 에디터 (/:id/sparql)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────┐   │
│  │  CodeMirror (SPARQL mode, h-64)               │   │
│  │  SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10  │   │
│  └────────────────────────────────────────────────┘   │
│  [▶ 실행]  [예제▼]  실행 시간: 45ms  결과: 10행       │
├────────────────────────────────────────────────────────┤
│  RESULTS TABLE (flex-1, 스크롤)                        │
│  s            │ p              │ o                     │
│  ex:Alice     │ rdf:type       │ ex:Person             │
│  ...                                                    │
└────────────────────────────────────────────────────────┘
```

### 6.6 Import (/:id/import)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├────────────────────────────────────────────────────────┤
│                                                        │
│  STEP 1 ──── STEP 2 ──── STEP 3                       │  ← 위저드 스텝
│  소스 선택     미리보기     완료                         │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │  [📁 파일 업로드]  [🔗 URL 입력]  [⭐ 사전등록]  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                        │
│  사전 등록 목록:                                        │
│  [ schema.org ] [ FOAF ] [ Dublin Core ] [ SKOS ]     │
│  [ OWL ]        [ RDFS ]                               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 6.7 Merge (/:id/merge)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├────────────────────────────────────────────────────────┤
│  [소스 온톨로지 선택 ▼]  [충돌 미리보기]               │
├──────────────────────┬─────────────────────────────────┤
│  현재 온톨로지        │  소스 온톨로지                  │
│  (Target)            │  (Source)                       │
│                      │                                 │
│  ex:Person           │  src:Person                     │
│    domain: ex:works  │    domain: src:works            │
│    ⚠ 충돌            │    ⚠ 충돌                       │
│   [유지] [덮어쓰기]  │                                 │
│                      │                                 │
├──────────────────────┴─────────────────────────────────┤
│  [병합 실행]  충돌 3건 / 자동병합 가능 12건             │
└────────────────────────────────────────────────────────┘
```

### 6.8 Reasoner (/:id/reasoner)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├────────────────────────────────────────────────────────┤
│  대상 범위:  ● 전체 온톨로지  ○ 서브그래프 선택        │
│                                                        │
│  [Entity 선택: _________________________ +추가]        │
│  선택됨: ex:Alice, ex:Person  [X]                     │
│                                                        │
│  [▶ 추론 실행]                                         │
├────────────────────────────────────────────────────────┤
│  RESULTS                                               │
│                                                        │
│  ✅ 정합성: 일관됨                                      │
│                                                        │
│  ⚠ 위반 (2건)                                          │
│  ┌──────────────────────────────────────────────────┐ │
│  │ CardinalityViolation  ex:Alice                   │ │
│  │ ex:hasManager 의 maxCardinality=1 초과            │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  💡 추론된 사실 (5건)                                   │
│  ex:Alice rdf:type ex:Employee  (Transitive 추론)      │
└────────────────────────────────────────────────────────┘
```

### 6.9 Sources (/:id/sources)

```
┌─ TOPBAR ──────────────────────────────────────────────┐
├────────────────────────────────────────────────────────┤
│  [+ 소스 추가]                                          │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │  HR DB (JDBC)              Concept: ex:Employee  │  │
│  │  상태: ✅ 활성   마지막 동기화: 5분 전   [동기화] │  │
│  │  [설정▼]  [매핑 편집]  [삭제]                    │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  근태 API (Stream)         Concept: ex:Employee  │  │
│  │  상태: ✅ 실시간   지연: 2초                     │  │
│  └─────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## 7. 색상 시스템 / 타이포그래피

### 7.1 색상 팔레트 (Foundry 스타일 다크 테마)

```css
/* ── 배경/표면 ── */
--color-bg-base:      #0D1117;   /* 최하위 배경 */
--color-bg-surface:   #161B22;   /* 카드, 패널 */
--color-bg-elevated:  #21262D;   /* 드롭다운, 모달 */
--color-border:       #30363D;   /* 구분선 */

/* ── 텍스트 ── */
--color-text-primary:   #E6EDF3;
--color-text-secondary: #8B949E;
--color-text-muted:     #484F58;

/* ── 브랜드/액션 ── */
--color-primary:        #2F81F7;   /* 버튼, 링크, 선택 상태 */
--color-primary-hover:  #388BFD;
--color-primary-subtle: #1F6FEB1A; /* 배경 강조 */

/* ── 상태 ── */
--color-success:        #3FB950;
--color-warning:        #D29922;
--color-error:          #F85149;
--color-info:           #79C0FF;

/* ── 그래프 노드/엣지 ── */
--color-node-concept:     #2F81F7;   /* 파란 원 — Concept */
--color-node-individual:  #3FB950;   /* 초록 원 — Individual */
--color-edge-object-prop: #A78BFA;   /* 보라 선 — ObjectProperty */
--color-edge-data-prop:   #FB923C;   /* 주황 선 — DataProperty */
--color-node-selected:    #F0A93F;   /* 선택된 노드 테두리 */
```

### 7.2 타이포그래피

| 용도 | 폰트 | 크기 | 굵기 |
|------|------|------|------|
| UI 기본 | Inter | 14px | 400 |
| 레이블/캡션 | Inter | 12px | 400 |
| 본문 | Inter | 14px | 400 |
| 소제목 | Inter | 16px | 600 |
| 섹션 제목 | Inter | 20px | 700 |
| 페이지 제목 | Inter | 24px | 700 |
| IRI 표시 | JetBrains Mono | 12px | 400 |
| SPARQL 에디터 | JetBrains Mono | 13px | 400 |
| 코드/Turtle 스니펫 | JetBrains Mono | 13px | 400 |

**폰트 로딩:** Google Fonts CDN (Inter 300/400/600/700, JetBrains Mono 400/700)

**행간:** `leading-relaxed` (1.625) 기본, `leading-tight` (1.25) 테이블

---

## 8. 반응형 브레이크포인트

**기본 방향:** Desktop-first (엔터프라이즈 도구 특성상 주 사용 환경은 1280px+ 모니터)

| 이름 | 픽셀 | 레이아웃 변화 |
|------|------|--------------|
| `2xl` | 1536px+ | 기본 — 사이드바 w-56, 상세 패널 w-96 |
| `xl` | 1280px | 기본과 동일 |
| `lg` | 1024px | 상세 패널 w-72로 축소; 그래프 캔버스 풀 기능 유지 |
| `md` | 768px | 사이드바 아이콘만 표시 (w-14); 상세 패널 모달로 전환 |
| `sm` | 640px | 사이드바 숨김 (Hamburger 메뉴); 단일 컬럼 레이아웃 |
| `xs` | <640px | 읽기 전용 뷰 (편집 기능 제한); 그래프 뷰 단순화 |

**핵심 제약:**
- SPARQL 에디터, 그래프 뷰, Merge diff는 `lg`(1024px) 미만에서 기능 제한 안내 배너 표시
- 최소 동작 보장 해상도: 1024 × 768

---

## 9. 백엔드 서비스 내부 설계

### 9.1 OntologyStore (Oxigraph 래퍼)

```python
class OntologyStore:
    """
    온톨로지별 Named Graph 관리 규칙:
    - TBox (스키마): <{ontology_iri}/tbox>
    - ABox (인스턴스, 소스별): <{source_id}/{timestamp}>
    - Reasoner 출력: <{ontology_iri}/inferred>
    """

    async def sparql_select(self, ontology_id: str, query: str) -> list[dict]: ...
    async def sparql_update(self, ontology_id: str, update: str) -> None: ...
    async def insert_triples(self, graph_iri: str, triples: list[Triple]) -> None: ...
    async def delete_graph(self, graph_iri: str) -> None: ...
    async def export_turtle(self, ontology_id: str) -> str: ...
```

### 9.2 SyncService (Oxigraph → Neo4j)

동기화 트리거:
1. TBox 변경 시 (Concept/Property 추가·수정·삭제) → 즉시 Neo4j 반영
2. ABox 대량 수집 후 → 배치 동기화 (5분 주기 또는 10만 triple 임계값)

```
Oxigraph SPARQL (전체 그래프)
         ↓  CONSTRUCT 쿼리로 노드/엣지 추출
Python 변환 레이어
  - owl:Class → (:Concept) 노드
  - owl:NamedIndividual → (:Individual) 노드
  - rdf:type → (:Individual)-[:TYPE]->(:Concept)
  - ObjectProperty 값 → 노드 간 관계
  - DataProperty 값 → 노드 속성
         ↓  UNWIND + MERGE Cypher (배치 1000건)
Neo4j
```

### 9.3 ReasonerService

```python
class ReasonerService:
    """
    owlready2 + HermiT (OWL 2 RL 기준)
    실행 흐름:
    1. Oxigraph에서 대상 서브그래프 CONSTRUCT → Turtle 임시 파일
    2. owlready2.get_ontology().load() → in-memory OWL 그래프
    3. sync_reasoner_hermit(infer_property_values=True, infer_data_property_values=True)
    4. 추론 결과(inferred triples) → Oxigraph inferred Named Graph에 저장
    5. 위반(Unsatisfiable classes 등) → ReasonerResult로 직렬화
    """
    async def run(self, ontology_id: str, entity_iris: list[str] | None) -> str: ...  # jobId
    async def get_result(self, job_id: str) -> ReasonerResult: ...
```

---

## 10. 수집 파이프라인 상세 설계

### 10.1 Kafka 토픽 구조

| 토픽 | 파티션 기준 | 메시지 형식 | 용도 |
|------|-----------|-----------|------|
| `raw-source-events` | source_id | JSON | 외부 소스 원본 이벤트 |
| `rdf-triples` | ontology_id | N-Triples | 변환된 RDF Triple |
| `sync-commands` | ontology_id | JSON | Oxigraph→Neo4j 동기화 트리거 |

### 10.2 RDF 변환 파이프라인

```
raw-source-events 메시지 구조:
{
  "source_id": "src-hr-jdbc",
  "ontology_id": "onto-001",
  "event_type": "upsert" | "delete",
  "timestamp": "2026-03-23T09:00:00Z",
  "records": [
    { "emp_id": 42, "name": "Alice", "dept": "Engineering" }
  ]
}

rdf_transformer.py 처리:
1. BackingSource 설정 로드 (iriTemplate, propertyMappings)
2. IRI 생성: iri_generator.generate(template, record)
3. rdf:type 트리플 생성: {iri} rdf:type {conceptIri}
4. 각 propertyMapping → DataProperty / ObjectProperty 트리플 생성
5. Named Graph IRI 결정: {source_id}/{timestamp}
6. N-Triples 직렬화 → rdf-triples 토픽 발행
```

### 10.3 CSV 파일 수집 파이프라인

#### 흐름

```
POST /sources/{id}/upload  (multipart CSV)
  │
  ├─ 서버: /uploads/{source_id}_{timestamp}.csv 저장
  │        헤더 파싱 → { fileUrl, rowCount, headers } 반환 (프리뷰용)
  │
POST /sources/{id}/sync  (업로드 후 즉시 or 수동 트리거)
  │
  ├─ [단계 1 — Oxigraph]
  │    csv.DictReader → 각 row에 대해:
  │      iri = iriTemplate.format(**row)        # PK 컬럼 치환
  │      RDFTransformer.transform(event, source) → list[Triple]
  │    named_graph = f"urn:source:{source_id}/{timestamp}"
  │    기존 named_graph DROP (재적재 시 원자적 교체)
  │    ontology_store.sparql_update(BULK INSERT into named_graph)
  │
  └─ [단계 2 — Neo4j LOAD CSV]
       file_url = f"http://backend:8000/static/uploads/{filename}"
       session.run("""
         LOAD CSV WITH HEADERS FROM $url AS row
         CALL {
           WITH row
           MERGE (n:Individual {iri: apoc.text.format($iriTemplate, [row[$pk]])})
           SET n.label    = row[$labelField],
               n.ontologyId = $ontologyId
           WITH n, row
           MERGE (c:Concept {iri: $conceptIri})
           MERGE (n)-[:TYPE]->(c)
         } IN TRANSACTIONS OF 500 ROWS
       """, url=file_url, iriTemplate=..., pk=..., ...)
```

**주의:** `apoc.text.format` 없이 단순 IRI 템플릿을 적용하려면 Python에서 Cypher 파라미터로 미리 치환된 IRI 목록을 UNWIND로 넘기는 방식도 사용 가능. APOC 플러그인이 없는 경우 이 방식 권장.

#### 단계별 실패 처리

| 실패 시점 | 동작 |
|-----------|------|
| 파일 업로드 실패 | 클라이언트에 오류 반환, 아무것도 변경 안 됨 |
| Oxigraph 단계 실패 | named_graph rollback (DROP), Neo4j 단계 미실행 |
| Neo4j 단계 실패 | Oxigraph 데이터는 보존됨 → `POST /sync`로 재시도 가능 |

#### JobResponse 반환 형식

```json
{
  "jobId": "uuid",
  "status": "completed",
  "result": {
    "rowsRead": 1240,
    "triplesInserted": 6200,
    "neo4jNodesUpserted": 1240,
    "namedGraph": "urn:source:src-csv-hr/2026-03-31T09:00:00"
  }
}
```

### 10.4 충돌 해결 (Conflict Resolution)

동일 IRI에 동일 DataProperty가 복수 소스에서 다른 값으로 들어올 때:

```
정책 A (user-edit-wins):
  - 수동 입력 Named Graph의 값이 존재하면 해당 값 우선
  - 소스 자동 수집 값은 보조 Named Graph에 보존 (Provenance 추적용)
  - SPARQL 쿼리 시: DEFAULT 그래프에 사용자 편집값만 노출

정책 B (latest-wins):
  - Named Graph의 prov:generatedAtTime 비교
  - 최신 타임스탬프 값만 DEFAULT 그래프에 노출
```

---

## 11. 오픈소스 라이브러리 및 도구 목록

### 11.1 백엔드

| 라이브러리 | 버전 (목표) | 용도 |
|-----------|------------|------|
| `fastapi` | 0.115+ | REST API 프레임워크 |
| `uvicorn` | 0.30+ | ASGI 서버 |
| `pydantic` | 2.x | 데이터 유효성 검사 / 직렬화 |
| `pyoxigraph` | 0.4+ | Oxigraph Python 바인딩 (RDF 저장소) |
| `rdflib` | 7.x | RDF 파싱 (Turtle, OWL, JSON-LD 등) |
| `owlready2` | 0.46+ | OWL 2 온톨로지 + HermiT 추론기 |
| `neo4j` | 5.x | Neo4j Python 드라이버 |
| `kafka-python` | 2.x | Kafka Producer / Consumer |
| `fastmcp` | 2.x | MCP 서버 |
| `httpx` | 0.27+ | 비동기 HTTP 클라이언트 (API Import용) |
| `python-multipart` | 0.0.9+ | 파일 업로드 처리 |

### 11.2 프론트엔드

| 라이브러리 | 버전 (목표) | 용도 |
|-----------|------------|------|
| `react` | 19.x | UI 프레임워크 |
| `react-router-dom` | 7.x | SPA 라우팅 |
| `typescript` | 5.x | 타입 안전성 |
| `tailwindcss` | 4.x | 유틸리티 CSS |
| `cytoscape` | 3.x | 그래프 시각화 |
| `cytoscape-dagre` | - | 계층형 온톨로지 레이아웃 |
| `@codemirror/lang-sparql` | - | SPARQL 문법 강조 (커뮤니티 패키지) |
| `@tanstack/react-query` | 5.x | 서버 상태 관리 / 캐싱 |
| `zustand` | 5.x | 클라이언트 상태 (선택된 노드 등) |
| `lucide-react` | 0.4+ | 아이콘 |

### 11.3 인프라

| 도구 | 용도 |
|------|------|
| Docker + Docker Compose | 컨테이너 오케스트레이션 |
| Nginx | 리버스 프록시 (SPA + API 라우팅) |
| Apache Kafka (bitnami 이미지) | 메시지 큐 |
| Neo4j Community Edition | LPG 저장소 |
| Ontop (선택, 별도 컨테이너) | Virtual KG (RDB → SPARQL) |

### 11.4 개발 도구

| 도구 | 용도 |
|------|------|
| Vite | 프론트엔드 빌드 |
| pytest + pytest-asyncio | 백엔드 테스트 |
| Vitest | 프론트엔드 테스트 |
| Ruff | Python 린터/포매터 |
| ESLint + Prettier | TypeScript 린터/포매터 |
