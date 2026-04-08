# 기획서: Palantir Foundry 온톨로지 플랫폼

**작성일:** 2026-03-23  
**버전:** 1.3 (구현 현황 반영)

---

## 1. 사이트 목적 및 타겟 사용자

### 목적
Palantir Foundry의 온톨로지 레이어를 재현한 웹 기반 플랫폼.
사용자가 도메인 지식을 Entity/Relation 구조로 모델링하고, AI Agent와 협업하여 탐색·추론·검증할 수 있는 시스템.

### 타겟 사용자
| 유형 | 설명 |
|------|------|
| 도메인 전문가 | 온톨로지를 직접 설계·편집하는 사람 |
| 데이터 분석가 | 온톨로지를 탐색하고 서브그래프를 쿼리하는 사람 |
| AI Agent | MCP를 통해 온톨로지를 읽고 추론하는 자동화 시스템 |

---

## 2. 핵심 기능 목록 (MoSCoW 우선순위)

### Must Have
- **온톨로지 CRUD**: Concept, Individual, Relation의 생성·수정·삭제
- **Entity 탐색**: Concept/Individual 이름, 속성 기반 검색 및 embedding 기반 vector search 검색
- **Relation 탐색**: 타입, 도메인/레인지, 속성 기반 검색 및 embedding 기반 vector search 검색
- **서브그래프 탐색**: 여러 Entity를 포함하는 서브그래프 쿼리 (SPARQL)
- **MCP 서버**: AI Agent가 온톨로지를 탐색·조회할 수 있는 MCP 인터페이스
- **표준 온톨로지 Import**: OWL/RDF/Turtle 파일 업로드 및 파싱 (schema.org, FOAF, Dublin Core 등)
- **온톨로지 Merge**: 두 개 이상의 온톨로지를 하나로 병합 (충돌 감지 포함)
- **다중 소스 Individual 수집**: RDB, API Stream, 수동 입력 등 소스별 수집 파이프라인 및 Concept 연결
- **Individual Provenance 추적**: 각 Individual의 소스·수집 시각·버전 메타데이터 관리

### Should Have
- **Reasoner (정합성 검증)**: 선택한 서브그래프에 대해 OWL 추론 실행, 모순·미충족 제약 리포트
- **그래프 시각화**: 노드-엣지 기반 인터랙티브 그래프 뷰
- **SPARQL 에디터**: 직접 SPARQL 쿼리 작성 및 실행

### Could Have
- **버전 관리**: 온톨로지 스냅샷 및 diff 뷰
- **접근 제어**: 온톨로지별 읽기/쓰기 권한 설정
- **Export**: OWL/Turtle/JSON-LD 형식으로 다운로드

### Won't Have (이번 버전)
- 실시간 협업 편집 (Google Docs 스타일)
- 자연어 → SPARQL 자동 변환

---

## 3. 온톨로지 데이터 모델

### OWL 2 핵심 구성요소

```
Ontology
  ├── Concept (owl:Class)                    ← 추상적 분류 개념
  │     ├── rdfs:subClassOf → Concept        ← 계층 관계
  │     ├── owl:equivalentClass → Concept    ← 동치 클래스
  │     ├── owl:disjointWith → Concept       ← 상호 배제 클래스
  │     └── meta: rdfs:label, rdfs:comment, IRI
  │
  ├── Individual (owl:NamedIndividual)        ← 실제 인스턴스
  │     ├── rdf:type → Concept               ← 클래스 멤버십
  │     ├── owl:sameAs → Individual          ← 동일 개체 선언
  │     ├── owl:differentFrom → Individual   ← 상이 개체 선언
  │     └── meta: rdfs:label, IRI
  │
  └── Relation (Property)
        ├── Object Property (owl:ObjectProperty)   ← 개체 간 관계
        │     ├── domain → Concept
        │     ├── range  → Concept
        │     ├── rdfs:subPropertyOf → ObjectProperty
        │     ├── owl:inverseOf → ObjectProperty
        │     └── 특성: Functional / InverseFunctional /
        │               Transitive / Symmetric /
        │               Asymmetric / Reflexive / Irreflexive
        │
        └── Data Property (owl:DatatypeProperty)   ← 개체 → 리터럴 값
              ├── domain → Concept
              ├── range  → xsd:string / xsd:integer /
              │            xsd:dateTime / xsd:boolean 등
              └── 특성: Functional
```

### Object Property vs Data Property 핵심 차이

| 구분 | Object Property | Data Property |
|------|-----------------|---------------|
| **range 타입** | 온톨로지 내 `owl:Class` (개체) | XML Schema 리터럴 (`xsd:*`) |
| **예시** | `hasFather`, `worksFor`, `locatedIn` | `hasAge`, `hasBirthDate`, `hasName` |
| **추론 활용** | 역관계 추론, 이행성 추론, cardinality 제약 | Functional 제약으로 유일 값 강제 |
| **LPG 매핑** | 노드 간 엣지(Relationship) | 노드의 속성(Property) |

### Cardinality 제약 (Restriction)

| 제약 | 의미 |
|------|------|
| `owl:minCardinality n` | 최소 n개의 관계 값 |
| `owl:maxCardinality n` | 최대 n개의 관계 값 |
| `owl:exactCardinality n` | 정확히 n개 |
| `owl:someValuesFrom C` | 적어도 하나의 값이 C의 인스턴스 |
| `owl:allValuesFrom C` | 모든 값이 C의 인스턴스 |
| `owl:hasValue v` | 특정 값 v를 가짐 |

**핵심 구분:**
- `Entity = Concept ∪ Individual`
- `Relation = ObjectProperty ∪ DataProperty`
- Reasoner는 OWL 2 RL 프로파일 기준으로 정합성 검증

---

## 4. 저장소 아키텍처

### 최종 채택: Apache Jena Fuseki (단일 SPARQL 서버)

초기 설계는 RDF Triplestore(Oxigraph) + LPG(Neo4j) 하이브리드였으나,
라이선스 비용(Neo4j Community) 및 이중 저장소 동기화 복잡성 문제로
**Apache Jena Fuseki(TDB2)로 단일화**했다.

```
Before:  FastAPI → pyoxigraph(Oxigraph) + neo4j driver(Neo4j) + SyncService
After:   FastAPI → httpx → Jena Fuseki (TDB2, Named Graph 지원)
```

```yaml
# docker-compose.yml Fuseki 서비스
fuseki:
  image: stain/jena-fuseki:5.3.0
  ports:
    - "3030:3030"
  volumes:
    - fuseki-data:/fuseki
  environment:
    - ADMIN_PASSWORD=admin
    - JVM_ARGS=-Xmx2g
  command: --tdb2 --update --loc /fuseki/ontology /ontology
```

### Fuseki HTTP 엔드포인트 매핑

| 기능 | 엔드포인트 | HTTP 메서드 |
|------|-----------|------------|
| SPARQL SELECT / ASK | `{fuseki_url}/{dataset}/sparql` | POST (application/sparql-query) |
| SPARQL UPDATE | `{fuseki_url}/{dataset}/update` | POST (application/sparql-update) |
| Graph Store (GSP) | `{fuseki_url}/{dataset}/data` | GET/PUT/DELETE |

### Named Graph 구조

| Named Graph IRI | 용도 |
|-----------------|------|
| `{ontology_iri}/kg` | 모든 TBox + ABox 데이터 (단일 진실 원본) |
| `urn:source:{source_id}/{timestamp}` | Provenance 추적용 소스별 Named Graph |

---

## 5. Multi-Dataset 지원 (Option B: Dataset Pool)

### 설계 원칙

- **OntologyStore 싱글톤 유지** — 하나의 인스턴스가 내부 httpx 클라이언트(연결 풀)를 보유
- **dataset은 메서드 파라미터로 전달** — URL을 호출 시점에 동적으로 조립
- **기본값 "ontology" 유지** — 하위 호환성 보장

### 아키텍처

```
Frontend
  └── DatasetSelector (Sidebar)
        └── DatasetContext (React Context)
              └── API 클라이언트 (dataset query param 자동 주입)
                    └── GET /ontologies/{id}/concepts?dataset=my-ds

Backend (FastAPI)
  └── 각 엔드포인트: dataset = Query("ontology")
        └── OntologyStore.sparql_select(query, dataset=dataset)
              └── POST http://fuseki:3030/{dataset}/sparql  ← 동적 URL
```

---

## 6. 다중 소스 Individual 수집 아키텍처

### 핵심 문제: 소스가 다른 Individual을 어떻게 하나의 Concept에 연결하는가?

Foundry의 MDO(Multi-Datasource Object Type) 개념을 W3C OWL/RDF로 구현한다.
각 Individual은 하나 이상의 **Backing Source**에서 비롯되며, 공통 Primary Key(IRI)를 통해 동일 Concept 인스턴스로 통합된다.

### IRI 생성 전략 (소스별)

| 소스 유형 | IRI 생성 방법 | 예시 |
|-----------|--------------|------|
| RDB (JDBC) | `{base}/{table}/{PK}` | `ex:employee/42` |
| API Stream | `{base}/{entity_type}/{source_id}` | `ex:sensor/device-001` |
| 수동 입력 | 사용자 지정 IRI 또는 UUID 자동 생성 | `ex:person/uuid-...` |
| 표준 온톨로지 Import | 원본 IRI 유지 | `schema:Person` |

### Individual Provenance 메타데이터

```turtle
GRAPH ex:source/jdbc-hr/2026-03-23T09:00:00 {
    ex:employee/42 rdf:type ex:Employee ;
                   ex:name "Alice" .
}
GRAPH ex:source/api-stream/attendance/2026-03-23T09:05:00 {
    ex:employee/42 ex:lastCheckin "09:00" .
}
```

---

## 7. 기술 스택

### Backend
| 선택 | 근거 |
|------|------|
| **Python + FastAPI** | rdflib, owlready2 등 SemanticWeb 생태계가 Python에 집중 |
| **Apache Jena Fuseki** (TDB2) | 오픈소스 SPARQL 1.1 서버, Named Graph 지원, Docker 운영 |
| **rdflib** | RDF 파싱·직렬화 (Turtle/RDF-XML/JSON-LD/N3/NT 통일) |
| **owlready2** | HermiT 기반 OWL 2 추론기 내장 |
| **httpx** | Fuseki HTTP 클라이언트 (비동기) |
| **FastMCP** | MCP 서버를 FastAPI와 단일 프로세스로 운영 |

### Frontend
| 선택 | 근거 |
|------|------|
| **React + TypeScript** | 컴포넌트 재사용, 타입 안전성 |
| **Cytoscape.js** | 온톨로지 그래프 시각화 특화 |
| **CodeMirror** | SPARQL 에디터 |
| **TailwindCSS** | 빠른 UI 구성 |

### 인프라
- **Docker Compose**: Backend + Frontend + Fuseki 컨테이너 구성
- **Nginx**: 리버스 프록시 (SPA + API 라우팅)

---

## 8. 페이지 구성 (사이트맵)

```
/                          ← 온톨로지 목록 + 빠른 탐색
├── /ontologies
│   ├── /new               ← 새 온톨로지 생성
│   └── /:id
│       ├── /graph         ← 그래프 시각화 뷰
│       ├── /entities      ← Entity(Concept+Individual) 탐색
│       ├── /relations     ← Relation 탐색
│       ├── /sparql        ← SPARQL 에디터
│       ├── /import        ← 외부 온톨로지 Import
│       ├── /merge         ← 온톨로지 Merge
│       └── /reasoner      ← 정합성 검증 (서브그래프 선택 → 추론 실행)
└── /mcp                   ← MCP 서버 상태 + 도구 목록 (디버그용)
```

---

## 9. MCP 도구 목록 (AI Agent용)

| 도구 | 설명 |
|------|------|
| `search_entities` | 이름/타입 기반 Entity 검색 |
| `search_relations` | 도메인/레인지/타입 기반 Relation 검색 |
| `get_subgraph` | 지정 Entity 집합의 서브그래프 반환 |
| `sparql_query` | SPARQL SELECT/ASK 실행 |
| `get_ontology_summary` | 온톨로지 통계 요약 |
| `list_ontologies` | 사용 가능한 온톨로지 목록 |
| `run_reasoner` | 서브그래프 정합성 검증 실행 |
| `add_individual` | Individual 추가 |
| `update_individual` | Individual 수정 |
| `delete_individual` | Individual 삭제 |
| `add_concept` | Concept(Class) 추가 |

---

## 10. 표준 온톨로지 Import 지원 형식

- **파일 업로드**: `.owl`, `.ttl` (Turtle), `.rdf` (RDF/XML), `.jsonld` (JSON-LD), `.n3`
- **URL 직접 Import**: HTTP로 공개된 온톨로지 URL 입력
- **사전 등록 온톨로지**: schema.org, FOAF, Dublin Core, OWL, RDFS, SKOS 원클릭 Import

---

## 11. 온톨로지 Merge 정책

병합 시 IRI 충돌 처리 전략:
1. **자동 병합**: 동일 IRI는 속성을 union으로 합침
2. **충돌 감지**: 동일 IRI에 상충되는 domain/range 정의가 있으면 사용자에게 선택 요청
3. **Prefix 분리**: 충돌 방지를 위해 소스 온톨로지 prefix를 네임스페이스에 반영

---

## 12. 레퍼런스 및 디자인 방향

**레퍼런스:**
- Palantir Foundry Ontology Manager UI
- Protégé (데스크탑 온톨로지 에디터)
- GraphDB Workbench

**디자인 방향:**
- Foundry 스타일: 다크 사이드바 + 밝은 메인 콘텐츠 영역
- 그래프 뷰 중심: 온톨로지를 시각적으로 탐색하는 것이 주된 UX
- 정보 밀도 높은 테이블/패널 (엔터프라이즈 툴 감성)

---

## 13. 구현 현황 (2026-04-08 기준)

### 13.1 백엔드 구현 완료 항목

#### API 엔드포인트 (`backend/api/`)
| 파일 | 기능 |
|------|------|
| `ontologies.py` | 온톨로지 CRUD, 통계(OntologyStats) |
| `concepts.py` | Concept CRUD, 계층 조회, individual_count (asyncio.gather 병렬화) |
| `individuals.py` | Individual CRUD, `_individual_pattern()` GRAPH 절 명시 |
| `properties.py` | ObjectProperty / DatatypeProperty CRUD |
| `subgraph.py` | Python-side iterative SPARQL BFS (최대 500 노드) |
| `search.py` | `search_entities()`, `search_relations()` (GROUP_CONCAT 단일 쿼리) |
| `sparql.py` | SPARQL SELECT/ASK 직접 실행 |
| `sources.py` | BackingSource CRUD, CSV/파일/URL import 트리거 |
| `import_.py` | OWL/Turtle/RDF-XML/JSON-LD/N3 파일·URL 업로드 |
| `graphs.py` | Named Graph 목록 조회, graph-level 통계 |
| `datasets.py` | Fuseki dataset 목록 조회 (`GET /api/v1/datasets`) |
| `reasoner.py` | owlready2 HermiT 추론 실행, 결과 반환 |
| `merge.py` | 온톨로지 병합 |

#### 서비스 레이어 (`backend/services/`)
| 파일 | 기능 |
|------|------|
| `ontology_store.py` | httpx 기반 Fuseki HTTP 클라이언트, Multi-dataset 동적 URL 조립 |
| `import_service.py` | rdflib 통일 파싱 (모든 RDF 포맷) |
| `reasoner_service.py` | owlready2 래퍼, rdflib.URIRef 기반 (pyoxigraph 제거) |
| `ingestion/csv_importer.py` | CSV → RDF Triple 변환, Named Graph 적재 |
| `ontology_graph.py` | `kg_graph_iri()` 헬퍼 (Named Graph IRI 생성) |

#### MCP (`backend/app_mcp/`)
- FastMCP 기반 11개 도구 구현
- 모든 도구에 `dataset: str = "ontology"` 파라미터 지원

### 13.2 프론트엔드 구현 완료 항목

#### 레이아웃 컴포넌트 (`frontend/src/components/layout/`)
| 컴포넌트 | 기능 |
|----------|------|
| `AppShell.tsx` | 전체 레이아웃 (사이드바 + 메인) |
| `Sidebar.tsx` | 온톨로지 목록, DatasetSelector 통합 |
| `DatasetSelector.tsx` | Fuseki dataset 드롭다운, DatasetContext 연동 |
| `OntologyTabs.tsx` | Graph / Entities / Relations / SPARQL / Import 탭 |
| `TopBar.tsx` | 상단 내비게이션 바 |

#### Graph 뷰 (`frontend/src/components/graph/`)
| 컴포넌트 | 기능 |
|----------|------|
| `GraphCanvas.tsx` | Cytoscape.js 기반 그래프 렌더링 |
| `EntityGraphPanel.tsx` | 선택된 Entity의 서브그래프 패널 |
| `EntityRightPanel.tsx` | 우측 패널 (Detail / Reasoner 탭) |
| `ImportPanel.tsx` | Graph 뷰 내 Import 패널 |
| `IndividualsSidebar.tsx` | Graph 뷰 내 Individual 사이드바 |
| `NamedGraphList.tsx` | Named Graph 목록 표시 |
| `GraphControls.tsx` | 레이아웃/필터 컨트롤 |
| `GraphLegend.tsx` | 노드/엣지 범례 |
| `NodeDetailPanel.tsx` | 노드 클릭 시 상세 패널 |

#### Entity 컴포넌트 (`frontend/src/components/entities/`)
| 컴포넌트 | 기능 |
|----------|------|
| `EntityDetailPanel.tsx` | Entity 상세 (embedded/standalone 모드) |
| `ConceptTreeView.tsx` | Concept 계층 트리 (lazy loading, toggle) |
| `ConceptTreeNode.tsx` | 트리 노드 (Individual 인라인 표시) |
| `EntityTable.tsx` | Entity 목록 테이블 |
| `EntitySearchBar.tsx` | Entity 검색바 |
| `ConceptForm.tsx` | Concept 생성·수정 폼 |
| `IndividualForm.tsx` | Individual 생성·수정 폼 |

#### 페이지 (`frontend/src/pages/ontology/`)
| 페이지 | 기능 |
|--------|------|
| `GraphPage.tsx` | 그래프 시각화 (더블클릭 노드 확장, BFS 서브그래프) |
| `EntitiesPage.tsx` | Entity 탐색 (Concept 트리 + Individual 인라인 + 다중 선택 우측 패널) |
| `RelationsPage.tsx` | Relation 탐색 (ObjectProperty / DatatypeProperty, 우측 패널) |
| `SPARQLPage.tsx` | SPARQL 에디터 + 결과 테이블 |
| `ImportPage.tsx` | OWL/Turtle/RDF-XML/URL Import UI |
| `ReasonerPage.tsx` | 서브그래프 선택 → OWL 추론 실행 + 결과 |
| `MergePage.tsx` | 온톨로지 병합 UI |
| `SourcesPage.tsx` | BackingSource 관리 + CSV Import |

#### React Context
- `DatasetContext.tsx`: 선택된 dataset을 앱 전체에 공유

### 13.3 해결된 주요 버그 및 개선

| 항목 | 내용 |
|------|------|
| `rdf:Property` + `rdfs:Class` 미지원 | entity/relation 판별 패턴에 추가 타입 지원 |
| `_individual_pattern()` GRAPH 절 누락 | Fuseki default graph 조회 → `GRAPH <{kg}>` 명시로 수정 |
| `search_relations()` N+1 쿼리 | GROUP_CONCAT 단일 쿼리로 교체 |
| `get_concept()` 순차 쿼리 | `asyncio.gather` 병렬화 (6개 쿼리 동시 실행) |
| OntologyStats 필드 매핑 오류 | 백엔드 응답 구조와 프론트엔드 매핑 일치 |
| `PaginatedResponse has_next` | 페이지네이션 마지막 페이지 판별 수정 |
| Reasoner inferred axioms storid → IRI | owlready2 내부 ID를 IRI로 변환 |
| ABox-only KG 호환 | TBox 없는 순수 ABox 온톨로지도 entity 조회 가능 |

### 13.4 미완료 항목

| 항목 | 우선순위 | 비고 |
|------|---------|------|
| Fix-1: MCP tools `kg_graph_iri` 통일 | 보통 | `_manual_graph()` 삭제 필요 (추후 테스트 후 진행) |
| Export (OWL/Turtle/JSON-LD) | 낮음 | Could Have |
| 버전 관리 (스냅샷/diff) | 낮음 | Could Have |
| 접근 제어 (온톨로지별 권한) | 낮음 | Could Have |

---

## 14. 마이그레이션 이력

### Neo4j + Oxigraph → Apache Jena Fuseki (2026-03-~04)

**배경:** Neo4j Community Edition 라이선스 비용 + Oxigraph 이중 저장소 동기화 복잡성

**제거된 파일:**
- `backend/services/graph_store.py` — Neo4j AsyncDriver 래퍼
- `backend/services/sync_service.py` — Oxigraph → Neo4j 동기화 서비스
- `backend/workers/sync_worker.py` — 동기화 워커

**주요 변경:**
- `ontology_store.py`: `pyoxigraph` → `httpx` 기반 Fuseki HTTP 클라이언트
- `import_service.py`: `pyoxigraph` → `rdflib` 통일 파싱
- `reasoner_service.py`: `from pyoxigraph import NamedNode` → `rdflib.URIRef`
- `backend/api/subgraph.py`: Neo4j Cypher BFS → Python-side iterative SPARQL BFS
- `docker-compose.yml`: neo4j 서비스 제거, Fuseki 추가
- `backend/requirements.txt`: `neo4j==5.23.0`, `pyoxigraph==0.4.0` 제거

---

## 15. Schema 탭 통합 계획 (Entities + Relations → Schema)

### 배경

현재 `Entities` 탭(Concepts + Individuals)과 `Relations` 탭(ObjectProperty + DataProperty)이 분리돼 있으나,
Properties는 항상 `domain: Concept → range: Concept/xsd:*` 구조이므로 서로 강하게 종속된다.
하나의 **Schema 탭**으로 통합하여 연결 관계를 즉시 파악할 수 있는 레이아웃으로 개편한다.

---

### 목표 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│  Graph | Schema | SPARQL | Sources | Merge | Reasoner           │
├────────────────────────┬────────────────────────────────────────┤
│  LEFT PANEL (38%)      │  RIGHT PANEL (62%)                     │
│  [Search all...]       │                                        │
│                        │  ┌── Concept 선택 시 ────────────────┐ │
│  ▼ Concepts  [Tree|Flat] [+ New]                               │ │
│  ───────────────────   │  │ Animal              (owl:Class)   │ │
│  ○ Animal              │  │ IRI: ex:Animal                   │ │
│    ├ Dog               │  │                                  │ │
│    └ Cat               │  │ [Detail]  [Relations]  [Instances]│ │
│  ○ Person              │  │                                  │ │
│                        │  │ Relations 탭:                    │ │
│  ▼ Properties  [All|Obj|Data] [+ New]                         │ │
│  ───────────────────   │  │  as domain:                      │ │
│  ≈ hasPet              │  │    · hasPet  (→ Animal)          │ │
│    Person ──→ Animal   │  │    · owns    (→ Animal)          │ │
│  ≈ hasOwner            │  │                                  │ │
│    Person ──→ Animal   │  │  as range:                       │ │
│  — name                │  │    · hasOwner (Person →)         │ │
│    Person ──→ xsd:str  │  │                                  │ │
│                        │  └──────────────────────────────────┘ │
│                        │                                        │
│                        │  ┌── Property 선택 시 ───────────────┐ │
│                        │  │ hasPet       (owl:ObjectProperty) │ │
│                        │  │ Domain: [Person]  ← 클릭 → 좌측   │ │
│                        │  │ Range:  [Animal]    Concept 포커스│ │
│                        │  │ Chars: Symmetric                 │ │
│                        │  └──────────────────────────────────┘ │
│                        │                                        │
│                        │  ┌── SubGraph + Reasoner ────────────┐ │
│                        │  │  (현재 EntityRightPanel 재사용)   │ │
│                        │  └──────────────────────────────────┘ │
└────────────────────────┴────────────────────────────────────────┘
```

---

### 연결 관계가 드러나는 핵심 포인트

| 위치 | 표현 방식 |
|------|---------|
| 좌측 Property 목록 | 각 항목 아래 `domain ──→ range` 인라인 표시 |
| Concept 선택 → Relations 탭 | 이 Class를 domain/range로 사용하는 Property 목록 |
| Property 선택 → Domain/Range | 클릭 가능한 배지 → 좌측 Concept 섹션으로 포커스 이동 |

---

### 변경 파일 목록

#### 신규 파일 (3개)

| 파일 | 내용 |
|------|------|
| `frontend/src/pages/ontology/SchemaPage.tsx` | 통합 페이지. 좌우 패널 레이아웃, 전체 상태 관리 |
| `frontend/src/components/schema/SchemaLeftPanel.tsx` | 좌측 패널: Concepts 섹션 + Properties 섹션 |
| `frontend/src/components/schema/SchemaDetailPanel.tsx` | 우측 상단 Detail 패널: Concept·Property 선택에 따른 컨텍스트 뷰 |

#### 수정 파일 (3개)

| 파일 | 변경 내용 |
|------|---------|
| `frontend/src/components/layout/OntologyTabs.tsx` | `entities`, `relations` 항목 제거 → `schema` 추가 |
| `frontend/src/App.tsx` | `/entities`, `/relations` 라우트 제거 → `/schema` 추가 |
| `frontend/src/pages/__tests__/SchemaPage.test.tsx` | 통합 테스트 신규 작성 |

#### 삭제 파일 (2개)

| 파일 | 이유 |
|------|------|
| `frontend/src/pages/ontology/EntitiesPage.tsx` | SchemaPage로 통합 |
| `frontend/src/pages/ontology/RelationsPage.tsx` | SchemaPage로 통합 |

---

### SchemaPage 상태 구조

```typescript
type SelectionKind = 'concept' | 'individual' | 'property' | null

interface SchemaPageState {
  // 선택
  selectedIri: string | null
  selectedKind: SelectionKind

  // 좌측 패널
  conceptSearch: string
  conceptViewMode: 'flat' | 'tree'
  conceptPage: number
  propertyFilter: 'all' | 'object' | 'data'
  propertySearch: string
  propertyPage: number

  // 우측 패널
  rightSubTab: 'detail' | 'relations' | 'instances'   // Concept 선택 시
  graphIris: string[]                                  // SubGraph용

  // 폼
  showConceptForm: boolean
  showPropertyForm: boolean
  editingItem: Concept | Individual | ObjectProperty | DataProperty | null
}
```

---

### SchemaDetailPanel 서브탭 구조

#### Concept 선택 시

| 탭 | 내용 | API 호출 |
|----|------|---------|
| **Detail** | label, IRI, comment, super/sub classes, restrictions | `getConcept()` |
| **Relations** | domain으로 사용되는 Properties / range로 사용되는 Properties | `searchRelations(q='', domainIri=iri)` + `searchRelations(q='', rangeIri=iri)` |
| **Instances** | 이 Class의 Individual 목록 | `listIndividuals(typeFilter=iri)` (기존 IndividualsSidebar 재사용) |

#### Property 선택 시 (서브탭 없음, 단일 뷰)

- Type badge (Object / Data)
- IRI, Label, Comment
- Domain: 클릭 가능한 IRIBadge → `setSelectedIri(domainIri)` + 좌측 Concepts 섹션 포커스
- Range: Object Property면 클릭 가능 / Data Property면 xsd 타입 텍스트
- Characteristics (Object Property만)
- Inverse Of (Object Property만)
- Edit / Delete 버튼

---

### 테스트 계획

`frontend/src/pages/__tests__/SchemaPage.test.tsx`

| 테스트 케이스 | 내용 |
|-------------|------|
| 초기 렌더링 | Concepts 섹션, Properties 섹션이 좌측에 표시됨 |
| Concept 클릭 | 우측 패널에 Detail 탭이 열림 |
| Concept Relations 탭 | domain/range에 해당 Concept을 쓰는 Property 목록 표시 |
| Concept Instances 탭 | 해당 Concept의 Individual 목록 표시 |
| Property 클릭 | 우측 패널에 domain → range 표시 |
| Property domain 클릭 | 좌측 Concepts 섹션에서 해당 Concept 포커스 |
| 탭 이름 | OntologyTabs에 "Schema" 항목이 있음 |

---

### 단계별 작업

- [x] Step 1: 테스트 작성 (`SchemaPage.test.tsx`)
- [x] Step 2: `SchemaLeftPanel.tsx` 구현
  - [x] Step 2-1: Concepts 섹션 (Tree/Flat 토글, + New 버튼)
  - [x] Step 2-2: Properties 섹션 (All/Object/Data 필터, `domain → range` 인라인 표시)
- [x] Step 3: `SchemaDetailPanel.tsx` 구현
  - [x] Step 3-1: Concept 선택 시 — Detail / Relations / Instances 서브탭
  - [x] Step 3-2: Property 선택 시 — Domain·Range 클릭 → Concept 포커스 콜백
  - [x] Step 3-3: 편집/생성 폼 인라인 통합
- [x] Step 4: `SchemaPage.tsx` 구현 (레이아웃 + 전체 상태 연결)
- [x] Step 5: `OntologyTabs.tsx` 수정 (schema 탭 추가, entities/relations 제거)
- [x] Step 6: `App.tsx` 수정 (라우트 변경)
- [x] Step 7: `EntitiesPage.tsx`, `RelationsPage.tsx` 삭제
- [x] Step 8: 테스트 통과 확인 (27/27 SchemaPage, 111/111 전체)

---

## 16. Schema 탭 레이아웃 개편 — 4열 + 하단 Graph/Reasoner 분리

### 배경

- Individuals 수가 많아 Graph에 포함하면 시각화가 과부하됨 → Graph를 **Concept 전용**으로 분리
- Individual 탐색을 위한 전용 열 추가 (Concept 선택 시 해당 Concept의 Individuals 리스트)
- Reasoner를 하단 전체 패널에서 **Graph 우측**으로 이동
- 하단 Graph 높이 **288px → 576px (2배)**

---

### 목표 레이아웃

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Graph | Schema | SPARQL | Sources | Merge | Reasoner                   │
├──────────────┬──────────────────┬──────────────┬──────────────────────  │
│  Concepts    │  Concept Detail  │  Individuals │  Individual Detail      │
│  Properties  │  [Detail]        │  (선택된     │                        │
│  (~20%)      │  [Relations]     │  Concept의)  │  IRI, types,           │
│              │  (~25%)          │  스크롤 목록  │  data/obj props        │
│              │                  │  (~20%)      │  (~35%)                │
├──────────────┴──────────────────┴──────────────┴────────────────────────┤
│  Graph (Concept 노드만, height=576px)    │  Reasoner                    │
│  (~65%)                                 │  (~35%)                       │
└─────────────────────────────────────────┴───────────────────────────────┘
```

---

### 변경 상세

#### 상단 4열 패널

| 열 | 너비 | 내용 | 변경 여부 |
|----|------|------|---------|
| 1열 | ~20% | SchemaLeftPanel (Concepts + Properties) | 기존 유지 |
| 2열 | ~25% | SchemaDetailPanel — **Instances 탭 제거** | 수정 |
| 3열 | ~20% | **IndividualsPanel** (신규) — Concept 선택 시 해당 Individuals 목록 | 신규 |
| 4열 | ~35% | **IndividualDetailPanel** (신규) — Individual 클릭 시 상세 정보 | 신규 |

#### 하단 2열 패널 (height=576px)

| 영역 | 너비 | 내용 | 변경 여부 |
|------|------|------|---------|
| 좌 | ~65% | **ConceptGraphPanel** — Concept 노드만 표시 (individual 노드 프론트엔드 필터링) | 신규/수정 |
| 우 | ~35% | **SchemaReasonerPanel** — 기존 Reasoner를 독립 컴포넌트로 추출 | 신규 |

---

### 신규 컴포넌트 상세

#### `IndividualsPanel.tsx`

- 선택된 Concept의 Individuals를 페이지네이션 목록으로 표시
- 각 항목: label + IRI badge + type chip
- 클릭 시 `onSelectIndividual(iri)` → 4열 IndividualDetailPanel 오픈
- Concept 미선택 시 placeholder 표시

#### `IndividualDetailPanel.tsx`

- `getIndividual(ontologyId, iri, dataset)` 호출
- 표시 항목:
  - IRI, label, types (클릭 시 해당 Concept 포커스)
  - Data Properties: property label → value
  - Object Properties: property label → target IRI (클릭 시 해당 Individual 포커스)
- Edit / Delete 버튼

#### `ConceptGraphPanel.tsx` (EntityGraphPanel 수정 또는 래퍼)

- 기존 `EntityGraphPanel`과 동일하나 API 응답에서 `kind === 'individual'` 노드를 **프론트엔드 필터링**으로 제거
- 별도 파일로 분리 (EntityGraphPanel은 다른 곳에서 그대로 사용)

#### `SchemaReasonerPanel.tsx`

- 기존 EntityRightPanel 내 Reasoner 섹션을 독립 컴포넌트로 추출
- `graphIris` prop으로 추론 대상 수신
- Run Reasoner 버튼, Profile 선택, 결과 표시 (기존 코드 그대로)

---

### 상태 변경 (SchemaPage)

```typescript
// 추가
const [selectedIndividualIri, setSelectedIndividualIri] = useState<string | null>(null)
const [conceptGraphIris, setConceptGraphIris] = useState<string[]>([])

// 제거
// graphIris (기존 general purpose) → conceptGraphIris로 대체
//   Individual 클릭은 graph에 추가하지 않음
//   Concept / Property 클릭만 conceptGraphIris에 추가
```

---

### 변경 파일 목록

#### 신규 파일 (4개)

| 파일 | 내용 |
|------|------|
| `frontend/src/components/schema/IndividualsPanel.tsx` | 3열: Concept의 Individuals 목록 |
| `frontend/src/components/schema/IndividualDetailPanel.tsx` | 4열: Individual 상세 |
| `frontend/src/components/schema/ConceptGraphPanel.tsx` | 하단 좌: Concept 전용 그래프 |
| `frontend/src/components/schema/SchemaReasonerPanel.tsx` | 하단 우: 독립 Reasoner 패널 |

#### 수정 파일 (3개)

| 파일 | 변경 내용 |
|------|---------|
| `frontend/src/pages/ontology/SchemaPage.tsx` | 4열 레이아웃 + 하단 2열, 상태 변경 |
| `frontend/src/components/schema/SchemaDetailPanel.tsx` | Instances 탭 제거 |
| `frontend/src/pages/__tests__/SchemaPage.test.tsx` | 새 레이아웃에 맞게 테스트 업데이트 |

---

### 단계별 작업

- [x] Step 1: 테스트 업데이트 (`SchemaPage.test.tsx`)
- [x] Step 2: `SchemaDetailPanel.tsx` — Instances 탭 제거
- [x] Step 3: `IndividualsPanel.tsx` 구현
- [x] Step 4: `IndividualDetailPanel.tsx` 구현
- [x] Step 5: `ConceptGraphPanel.tsx` 구현
- [x] Step 6: `SchemaReasonerPanel.tsx` 구현
- [x] Step 7: `SchemaPage.tsx` 레이아웃 개편 (4열 상단 + 2열 하단 576px)
- [x] Step 8: 테스트 통과 확인 (`SchemaPage.test.tsx` 30/30 통과)


---


---

## 17. Named Graph per Import 분리 + Graph 선택 필터

**날짜:** 2026-04-08

### 목표

1. 수동 생성 데이터(Concept/Property/Individual UI 생성) → `{ont_iri}/manual`
2. Import 파일/URL/표준 별 독립 Named Graph
3. NamedGraph 체크박스 선택 → 선택된 그래프에서만 모든 기능 동작
4. (후속) 각 Named Graph TTL 편집기

### Named Graph IRI 규칙

| 소스 | Named Graph IRI |
|------|----------------|
| UI 수동 생성 | `{ont_iri}/manual` |
| 파일 import | `{ont_iri}/imports/{filename}` |
| URL import | `{ont_iri}/imports/url/{hostname_path_slug}` |
| 표준 import | `{ont_iri}/imports/standard/{name}` |

### 아키텍처 변경

```
현재:
  모든 쓰기/읽기 → GRAPH <{ont_iri}/kg>

변경 후:
  수동 쓰기   → GRAPH <{ont_iri}/manual>
  import 쓰기 → GRAPH <{ont_iri}/imports/...>

  읽기 (선택된 그래프 기준):
    GRAPH ?_g { ... }
    FILTER(?_g IN (<iri1>, <iri2>, ...))
```

- **기본 선택값:** 온톨로지에 속한 모든 Named Graph (처음 로드 시 전체 체크)
- **쓰기(INSERT/UPDATE/DELETE):** 항상 `/manual` 또는 해당 import graph 사용 (선택과 무관)

### 구현 단계

#### Part A — Backend: Named Graph IRI 분리

- [x] **A1** `services/ontology_graph.py`
  - [x] `manual_graph_iri(ont_iri)` 추가: `{ont_iri}/manual`
  - [x] `import_graph_iri(ont_iri, source_type, source_label)` 추가
  - 기존 `kg_graph_iri` 유지 (subgraph backward-compat용)
- [x] **A2** `api/import_.py` — 3개 엔드포인트 `import_graph_iri` 사용
- [x] **A3** 수동 쓰기 쿼리 전환
  - `api/concepts.py`, `api/properties.py`, `api/individuals.py`
  - INSERT/DELETE → `GRAPH <{manual_iri}>`

#### Part B — Backend: Graph 선택 필터

- [x] **B1** 공통 헬퍼 `_graphs_filter(graph_iris)` 추가
  - `graph_iris` 없으면 → `STRSTARTS(STR(?_g), "{ont_prefix}")` (전체 조회)
  - `graph_iris` 있으면 → `?_g IN (<iri1>, <iri2>...)` 필터
- [x] **B2** `api/concepts.py` SELECT 쿼리 변환 (`GRAPH ?_g + filter`)
- [x] **B3** `api/properties.py` SELECT 쿼리 변환
- [x] **B4** `api/individuals.py` SELECT 쿼리 변환
- [x] **B5** `api/search.py` SELECT 쿼리 변환
- [x] **B6** `api/subgraph.py` BFS + 엣지 쿼리 변환
- [x] **B7** 모든 list/get 엔드포인트 — `graph_iris: list[str] = Query(default=[])` 파라미터 추가

#### Part C — Frontend: Named Graph 선택 UI

- [x] **C1** `NamedGraphsContext.tsx` 추가 — 선택된 graph IRI 목록 전역 관리
- [x] **C2** `NamedGraphList.tsx` — 체크박스 추가, 전체선택/해제 버튼, 로드 시 전체 자동 선택
- [x] **C3** `api/entities.ts`, `api/relations.ts`, `api/ontologies.ts` — 모든 list/get 함수에 `graphIris?: string[]` 파라미터 추가
- [x] **C4** 모든 useQuery 호출에 선택된 graph IRI 전달
  - `SchemaLeftPanel`, `ConceptGraphPanel`, `IndividualsPanel`, `SchemaDetailPanel`
  - `ConceptTreeView`, `ConceptTreeNode`, `IndividualsSidebar`
  - `useEntitySearch`, `useSearchRelations`, `useSubgraph`
  - `App.tsx`: `NamedGraphsProvider` per-ontology (`key={ontologyId}`)
  - `SPARQLPage`는 사용자가 직접 GRAPH 지정하므로 제외

#### Part D — 테스트

- [x] **D1** Backend 테스트: `import/file` 후 named graph IRI 검증 (`/imports/{filename}`)
- [x] **D2** Backend 테스트: `graph_iris` 파라미터로 선택된 그래프만 조회되는지 검증
- [x] **D3** Frontend 테스트: `NamedGraphList` 체크박스 토글 UI
- [x] **D4** Frontend 테스트: 특정 graph 선택 시 해당 데이터만 반환

**실제 반영 산출물 (2026-04-08):**
- `frontend/src/pages/__tests__/SchemaPage.test.tsx`: `NamedGraphsProvider` 래핑 후 30/30 통과
- `frontend/src/components/graph/__tests__/NamedGraphList.test.tsx`: 체크박스 토글/전체선택-해제 테스트 추가
- `frontend/src/hooks/__tests__/useEntitySearch.test.tsx`: 선택된 `graph_iris` 필터 전달 검증 테스트 신규 추가
- `frontend/src/components/graph/NamedGraphList.tsx`: checkbox 이벤트 중복 토글 방지 (`readOnly + onClick` 패턴)

#### Part E — 후속: TTL 편집기

- [ ] **E1** `GET /ontologies/{id}/graphs/{graph_iri_encoded}/ttl` — GSP GET으로 TTL 반환
- [ ] **E2** `PUT /ontologies/{id}/graphs/{graph_iri_encoded}/ttl` — TTL 교체 (GSP PUT)
- [ ] **E3** Frontend `NamedGraphList` — 편집 버튼 + CodeMirror TTL 편집기 패널

### 다음 작업 순서 (고정)

- [x] **S1** Section 16 / Step 8 — Schema 레이아웃 관련 테스트 재실행 및 통과 확인
- [x] **S2** Section 17 / Part D3 — `NamedGraphList` 체크박스 토글 프론트 테스트 작성/통과
- [x] **S3** Section 17 / Part D4 — 선택 graph 필터 반영 프론트 테스트 작성/통과
- [ ] **S4** Section 17 / Part E1 — TTL 조회 API 구현 + 테스트
- [ ] **S5** Section 17 / Part E2 — TTL 교체 API 구현 + 테스트
- [ ] **S6** Section 17 / Part E3 — TTL 편집기 UI(CodeMirror) 구현 + 테스트

---

## 18. 긴급 버그 — Import 후 Schema Graph 미표시

**날짜:** 2026-04-08

### 증상

- Graph import는 성공하지만 `Schema` 탭 하단 `ConceptGraphPanel`에서 `No concepts to display`가 표시됨

### 원인 (확인)

- 프론트 `ConceptGraphPanel`이 `listConcepts`, `listObjectProperties` 호출 시 `pageSize=200` 전달
- 백엔드 `concepts/properties` API는 `page_size <= 100` 검증 제한
- 결과적으로 요청이 422로 실패하며 그래프 데이터가 비어 보임

### 단계별 작업

- [ ] **G1** 테스트: `ConceptGraphPanel`이 `page_size=100`으로 호출되는지 검증 테스트 작성
- [ ] **G2** 구현: `ConceptGraphPanel`의 page size 상수 조정 (`200 → 100`)
- [ ] **G3** 검증: `ConceptGraphPanel` 테스트 통과 + SchemaPage 회귀 테스트 재실행
- [x] **G1** 테스트: `ConceptGraphPanel`이 `page_size=100`으로 호출되는지 검증 테스트 작성
- [x] **G2** 구현: `ConceptGraphPanel`의 page size 상수 조정 (`200 → 100`)
- [x] **G3** 검증: `ConceptGraphPanel` 테스트 통과 + SchemaPage 회귀 테스트 재실행

---

## 19. 긴급 버그 — DataProperty range에 `rdfs:Literal` 포함 시 500

**날짜:** 2026-04-08

### 증상

- `GET /ontologies/{id}/properties?kind=data` 호출 시 500 발생
- 스택트레이스: `DataProperty.range` 검증에서 `rdfs:Literal` 값 거부

### 원인 (확인)

- `_fetch_data_property()`가 `rdfs:range` 값을 수집할 때 `rdfs:Literal`을 허용 목록으로 변환하지 않음
- `DataProperty.range` 모델은 현재 `xsd:*` literal union만 허용

### 단계별 작업

- [x] **R1** 테스트: `rdfs:Literal` range가 포함된 DataProperty 조회 테스트 추가 (재현)
- [x] **R2** 구현: 모델/변환 로직에 `rdfs:Literal` 호환 추가
- [x] **R3** 검증: properties 관련 테스트 + SchemaPage 회귀 테스트 통과

---

## 20. 디버깅 — Entity 수정/저장 시 에러

**날짜:** 2026-04-08

### 가설 (우선순위)

1. Concept restriction의 `hasValue`가 literal인데 IRI 형태(`<...>`)로 직렬화되어 저장 쿼리 실패
2. (후순위) Individual 수정 payload의 필드 불일치로 422

### 단계별 작업

- [x] **EBUG-1** 재현 테스트: `hasValue` literal restriction 직렬화 포맷 검증 테스트 추가
- [x] **EBUG-2** 수정: `hasValue` 값이 literal일 때 SPARQL literal로 직렬화
- [x] **EBUG-3** 검증: concepts 관련 테스트 + 신규 테스트 통과

---

## 21. 디버깅 — Individual 수정 payload 검증 에러(422)

**날짜:** 2026-04-08

### 가설

- 프론트 Individual 저장 payload에는 `graph_iri`가 없는데,
- 백엔드 `DataPropertyValue` / `ObjectPropertyValue` 모델은 `graph_iri`를 필수로 요구해서 422 발생

### 단계별 작업

- [x] **IBUG-1** 재현 테스트: `graph_iri` 없는 Individual update payload가 현재 실패함을 테스트로 고정
- [x] **IBUG-2** 수정: Individual 입력 모델에서 `graph_iri` 비필수 처리
- [x] **IBUG-3** 검증: 신규 테스트 + 관련 회귀 테스트 통과

---

## 22. Schema 시각화 개선 계획 — Protégé 스타일 의미 기반 뷰

**날짜:** 2026-04-08

### 문제 정의

현재 Schema 그래프/패널은 RDF 트리플 원형에 가까워서 사용자 관점에서 다음 문제가 있다.

- `b1`, `b2` 같은 blank node(Restriction 내부 노드) 노출
- 엔티티 라벨이 IRI 원문 위주로 보여 가독성 저하
- 의미적으로 중요한 관계(`subClassOf`, domain/range, inverseOf)와 보조 트리플이 혼재
- 그래프가 "온톨로지 편집을 돕는 뷰"가 아니라 "RDF 디버그 뷰"처럼 보임

### 기존 구현 vs 목표 구현 (비교)

| 항목 | 현재 구현(As-Is) | 목표 구현(To-Be) |
|------|------------------|------------------|
| 노드 구성 | API 결과 기반 노드 생성 시 RDF 보조 리소스가 유입될 수 있음 | `Concept`, `ObjectProperty`, `DatatypeProperty`, `Individual`만 노출 (의미 객체만) |
| blank node 처리 | 명시 필터 없음(경로에 따라 노출 가능) | UI/백엔드 양단에서 bnode 완전 차단 (`isBlank` 필터 + kind 화이트리스트) |
| 라벨 전략 | IRI fallback 비중이 큼 | `rdfs:label` 우선, 없으면 prefix 축약(`ex:Person`), 최후에 localName |
| 관계 표현 | 트리플 기반 엣지가 섞임 | 관계 유형별 명시 렌더링: `subClassOf`, `domain→range`, `instanceOf`, `inverseOf` |
| 패널/그래프 일관성 | 좌측 목록/우측 상세/그래프의 명명 규칙이 다름 | 공통 `displayName(entity)` 규칙으로 모든 화면 동기화 |
| 사용자 인지 부하 | 기술적 RDF 디테일 노출 | OWL 의미 모델 중심으로 축약/정규화 |

### 설계 원칙

1. **Semantic-first**: RDF 내부 구조보다 OWL 의미 객체를 우선 노출
2. **One naming policy**: 전 컴포넌트 동일 라벨 규칙 사용
3. **Dual guard**: 노이즈 제거는 백엔드 쿼리 + 프론트 렌더에서 이중 방어
4. **Backward-safe**: API 계약은 유지하고, 표현 계층부터 점진 개선

### 구현 범위 (Phase 분리)

#### Phase 1 — 표시 노이즈 제거 (빠른 체감 개선)

- blank node UI 노출 금지
- 라벨 표시 유틸 도입 (`displayName`, `compactIri`)
- Graph/Schema 패널에서 IRI 원문 대신 의미 라벨 우선 노출

**대상 파일(예상):**
- `frontend/src/components/schema/ConceptGraphPanel.tsx`
- `frontend/src/components/schema/SchemaLeftPanel.tsx`
- `frontend/src/components/schema/SchemaDetailPanel.tsx`
- `frontend/src/components/schema/IndividualDetailPanel.tsx`
- `frontend/src/components/shared/IRIBadge.tsx` (필요 시)
- `frontend/src/utils/iri.ts` (신규)

#### Phase 2 — 의미 관계 정규화

- 그래프 엣지 타입을 의미 단위로 한정:
  - `subClassOf`
  - `domain→range` (Object/Data Property)
  - `rdf:type` (Individual → Concept)
- Restriction/메타 트리플은 그래프 엣지에서 제거하고 우측 Detail 텍스트로만 표현

**대상 파일(예상):**
- `frontend/src/components/schema/ConceptGraphPanel.tsx`
- `frontend/src/components/graph/GraphLegend.tsx`
- `frontend/src/types/*` (edge kind 확장 시)

#### Phase 3 — 백엔드 응답 정제(선택)

- 검색/목록 API에서 시스템 predicate/range 노이즈 최소화
- 필요 시 `display_label` 계산 필드 제공(하위호환 유지)

**대상 파일(예상):**
- `backend/api/concepts.py`
- `backend/api/properties.py`
- `backend/api/individuals.py`

### 난이도 높은 지점 (리스크)

1. **라벨 공백 케이스**: import 온톨로지는 라벨 없는 엔티티가 많음  
   → prefix 축약 규칙 미정이면 다시 IRI 원문 회귀 가능
2. **제약식 표현 손실 우려**: Restriction bnode를 숨길 때 정보 손실로 오해 가능  
   → Detail 패널에서 restriction 블록은 유지
3. **성능**: 표시명 계산/정규화가 대량 노드에서 비용 증가 가능  
   → memoization + query select 최소화 필요
4. **회귀 범위 큼**: Schema, Graph, Search UI 전반에 영향  
   → 단계별 feature flag 또는 작은 PR 분할 권장

### 테스트 전략 (각 Phase 공통)

- **단위 테스트**
  - `displayName()` 규칙: label > compactIri > localName
  - blank node 입력 시 렌더 대상 제외
- **컴포넌트 테스트**
  - `ConceptGraphPanel`에서 bnode 미표시
  - 동일 엔티티가 좌/우/그래프에서 동일 라벨 사용
- **회귀 테스트**
  - 기존 `SchemaPage.test.tsx` 전체
  - `NamedGraphList` 필터 연동 상태에서 그래프 렌더 정상

### 작업 체크리스트 (구현 전용)

- [x] **VIZ-1** 기준선 테스트 추가: bnode 노출/IRI 원문 노출 현재 동작 고정
- [x] **VIZ-2** 공통 라벨 유틸(`displayName`, `compactIri`) 도입 + 기존 화면 적용
- [x] **VIZ-3** 그래프 노드/엣지 화이트리스트 적용(의미 객체만)
- [x] **VIZ-4** Restriction은 Detail 패널 유지, 그래프에서는 제외
- [x] **VIZ-5** Schema/Graph 회귀 테스트 통과 + 성능 스모크 확인
- [x] **VIZ-6** 사용자 검수 포인트 반영(라벨/필터/가독성)

### VIZ-6 반영 결과 (2026-04-08)

- 라벨 가독성:
  - 그래프 노드 라벨에서 raw IRI를 축약 표시로 정규화
  - 선택 chip / 패널 표시는 local name 중심으로 통일
- 노이즈 제거:
  - blank node(`_:`) 노드 시각화 제외
  - OWL restriction 관련 엣지(`someValuesFrom`, `allValuesFrom`, `hasValue`, cardinality 계열) 제외
- 필터 UX/회귀 안정성:
  - Named Graph 선택 필터 유지 상태에서 Schema/Graph 회귀 테스트 통과
  - 대량 payload 스모크 테스트에서 노이즈 필터 동작 확인

검수 근거 테스트:
- `frontend/src/components/graph/__tests__/EntityGraphPanel.test.tsx`
- `frontend/src/pages/__tests__/SchemaPage.test.tsx`
- `frontend/src/components/schema/__tests__/ConceptGraphPanel.test.tsx`
- `frontend/src/components/graph/__tests__/NamedGraphList.test.tsx`

### 완료 기준 (Definition of Done)

- Schema 탭에서 blank node(`_:`/`b1` 등) 노드가 시각적으로 0건
- 주요 엔티티(Concept/Property/Individual) 이름이 IRI 원문 대신 의미 라벨로 표시
- 그래프 엣지가 의미 관계 집합으로만 구성됨
- 기존 편집/저장/필터 기능 회귀 없음 (기존 테스트 + 신규 테스트 통과)

---

## 23. Schema 탭 패널 크기 조절 (Resizable Panels)

**날짜:** 2026-04-08

### 목표

Schema 탭의 각 패널(열/행) 경계를 드래그하여 크기를 자유롭게 조절할 수 있게 한다.
마지막으로 조절한 크기는 localStorage에 저장하여 새로고침 후에도 유지된다.

### 대상 경계

| 위치 | 경계 |
|------|------|
| 상단 4열 | Col1\|Col2, Col2\|Col3, Col3\|Col4 (수평) |
| 상하 분리 | TOP 영역 ↕ BOTTOM 영역 (수직) |
| 하단 2열 | Graph\|Reasoner (수평) |

### 기술 선택

- **`react-resizable-panels`** — 경량 라이브러리, PanelGroup/Panel/PanelResizeHandle API 제공, localStorage 자동 저장(`autoSaveId`) 지원

### 구현 상세

#### 컴포넌트 구조 변경

```
SchemaPage
  PanelGroup (direction="vertical" autoSaveId="schema-vertical")
    Panel (defaultSize=60, minSize=30)         ← 상단 TOP 영역
      PanelGroup (direction="horizontal" autoSaveId="schema-top-horizontal")
        Panel (defaultSize=20, minSize=10)     ← Col1: SchemaLeftPanel
        PanelResizeHandle
        Panel (defaultSize=25, minSize=10)     ← Col2: SchemaDetailPanel
        PanelResizeHandle                      ← Col3 존재 시만 렌더
        Panel (defaultSize=25, minSize=10)     ← Col3: IndividualsPanel
        PanelResizeHandle                      ← Col4 존재 시만 렌더
        Panel (defaultSize=30, minSize=10)     ← Col4: IndividualDetailPanel
    PanelResizeHandle
    Panel (defaultSize=40, minSize=20)         ← 하단 BOTTOM 영역
      PanelGroup (direction="horizontal" autoSaveId="schema-bottom-horizontal")
        Panel (defaultSize=60, minSize=20)     ← Graph
        PanelResizeHandle
        Panel (defaultSize=40, minSize=15)     ← Reasoner
```

#### `PanelResizeHandle` 스타일

- 수평 핸들: 너비 4px, 커서 `col-resize`, hover 시 primary 색상 강조
- 수직 핸들: 높이 4px, 커서 `row-resize`, hover 시 primary 색상 강조

### 작업 체크리스트

- [x] **RZ-1** `react-resizable-panels` 패키지 설치
- [x] **RZ-2** `ResizeHandle` 공통 컴포넌트 작성 (`frontend/src/components/shared/ResizeHandle.tsx`)
- [x] **RZ-3** 테스트 작성 (`SchemaPage.test.tsx` — 패널이 렌더되는지, ResizeHandle이 존재하는지 검증)
- [x] **RZ-4** `SchemaPage.tsx` — 수직 PanelGroup으로 TOP/BOTTOM 분리
- [x] **RZ-5** `SchemaPage.tsx` — TOP 영역 수평 PanelGroup으로 4열 변환
- [x] **RZ-6** `SchemaPage.tsx` — BOTTOM 영역 수평 PanelGroup으로 2열 변환
- [x] **RZ-7** 테스트 통과 확인 (전체 회귀 포함) — 34/34 passed
- [x] **RZ-8** `docs/plan.md` 업데이트

---

## Section 24 — react-resizable-panels v2 API 복원

### 배경
`react-resizable-panels`를 버전 지정 없이 설치해 v4.9.0이 설치됨.
v4는 export 이름이 완전히 바뀌어(`PanelGroup`→`Group`, `PanelResizeHandle`→`Separator`) 코드가 오동작.
`package.json`을 `^2.1.9`로 수정했으나 코드는 아직 v4 API 사용 중.

### 작업 체크리스트

- [x] **RV-1** `ResizeHandle.tsx` — `Separator` → `PanelResizeHandle`, import 복원
- [x] **RV-2** `SchemaPage.tsx` — `Group as PanelGroup` → `PanelGroup` import 복원
- [x] **RV-3** `SchemaPage.test.tsx` mock — `PanelGroup`/`PanelResizeHandle` 복원 + v2 export 검증 테스트 추가
- [x] **RV-4** 테스트 통과 확인 — SchemaPage 34/34, ResizeHandle 5/5
- [x] **RV-5** 컨테이너 볼륨 포함 재시작 확인 (`docker compose down -v && up -d`)
- [x] **RV-6** `docs/plan.md` 업데이트

---

## Section 25 — Concept 리스팅 Protege 방식으로 전환

### 현재 방식 vs Protege 방식 비교

#### 현재 (`_CLASS_PATTERN`)
```sparql
{ ?iri a owl:Class }
UNION { ?iri a rdfs:Class }
UNION { ?iri a skos:Concept }
UNION { [] rdf:type ?iri }          ← ABox instance의 type → 암묵적 클래스 추론
UNION { ?iri rdfs:subClassOf [] }   ← subClassOf 참여만으로도 클래스 취급
UNION { [] rdfs:subClassOf ?iri }
```

문제: ABox-only 데이터의 노이즈 클래스 포함, 외부 vocabulary IRI 오염 가능성

#### Protege 방식 (`getClassesInSignature()`)
OWL API 기준: **온톨로지 TBox axiom에 명시적으로 등장하는 named class만** 반환
- `rdf:type owl:Class` 로 선언된 클래스
- `rdfs:subClassOf` axiom에 등장하는 named class (단, `owl:Thing`/`rdfs:Resource` 제외)
- `owl:equivalentClass`, domain/range 선언에 등장하는 named class

레이블: `rdfs:label` → `skos:prefLabel` 우선순위, 언어 태그 필터, IRI fragment 폴백

---

### 변경 범위

**백엔드 `api/concepts.py`**

`_CLASS_PATTERN` 교체:
```sparql
-- Before (현재)
{ [] rdf:type ?iri }              ← 제거 (ABox 노이즈)
{ ?iri rdfs:subClassOf [] }       ← 유지 (TBox axiom)
{ [] rdfs:subClassOf ?iri }       ← 유지 (TBox axiom)

-- After (Protege 방식)
{ ?iri a owl:Class }
UNION { ?iri a rdfs:Class . FILTER NOT EXISTS { ?iri a owl:Ontology } }
UNION { ?iri a skos:Concept }
UNION { ?iri rdfs:subClassOf ?_any . FILTER(isIRI(?_any)) }    ← subClassOf subject
UNION { ?_any rdfs:subClassOf ?iri . FILTER(isIRI(?_any)) }    ← subClassOf object
UNION { ?_p rdfs:domain ?iri }    ← property domain
UNION { ?_p rdfs:range  ?iri }    ← property range
```

레이블 쿼리: `rdfs:label` 우선, `skos:prefLabel` 폴백 추가
```sparql
OPTIONAL { GRAPH ?_lg { ?iri rdfs:label ?lbl } }
OPTIONAL { GRAPH ?_lg { ?iri <http://www.w3.org/2004/02/skos/core#prefLabel> ?skosLbl } }
BIND(COALESCE(?lbl, ?skosLbl) AS ?label)
```

---

### 작업 체크리스트

- [x] **PC-1** 현재 `_CLASS_PATTERN` 문제점 테스트 작성 (ABox 노이즈 클래스 미포함 검증) — 4개 테스트 작성, 2개 실패로 시작
- [x] **PC-2** `_CLASS_PATTERN` → Protege 방식으로 교체 (`[] rdf:type ?iri` 제거, domain/range 패턴 추가)
- [x] **PC-3** 레이블 쿼리에 `skos:prefLabel` 폴백 추가 (`COALESCE(?_rdfsLbl, ?_skosLbl)`)
- [x] **PC-4** `list_subclasses`도 동일하게 적용
- [x] **PC-5** 테스트 통과 확인 — 4/4 passed, 회귀 없음
- [x] **PC-6** `docs/plan.md` 업데이트

---

## Appendix — Protege 클래스 로딩 방식 분석

> 참고: https://github.com/protegeproject/protege

### 사용 라이브러리

**OWL API (OWLAPI) 4.5.29** (`net.sourceforge.owlapi:owlapi-osgidistribution`)
Protege는 자체 파싱 없이 OWL API에 완전 위임. OSGi(Apache Felix 7.0.5) 위에서 동작.

---

### 클래스 목록 로딩

핵심 메서드: `OWLOntology.getClassesInSignature()`

```java
// OWLEntityRenderingCacheImpl.rebuild()
for (OWLOntology ont : owlModelManager.getOntologies()) {
    for (OWLClass cls : ont.getClassesInSignature()) {
        addRendering(cls, owlClassMap);  // 렌더링 문자열 → OWLClass 캐시
    }
}
```

IRI로 조회: `OWLEntityFinderImpl.getEntities(IRI)` → `ont.containsClassInSignature(iri)`

---

### rdfs:label / 메타데이터 읽기

```java
// AnnotationValueShortFormProvider.getShortForm()
for (OWLOntology ontology : ontologies) {
    for (OWLAxiom ax : ontology.getAnnotationAssertionAxioms(entity.getIRI())) {
        ax.accept(checker);  // Visitor 패턴으로 리터럴 추출
    }
}
// 어노테이션 없으면 IRI fragment 폴백
```

우선순위: `rdfs:label` → `skos:prefLabel` → 언어 태그 필터(ko>en 등) → IRI 마지막 세그먼트

기본 설정(`OWLRendererPreferences`):
```java
DEFAULT_ANNOTATION_IRIS = [
    OWLRDFVocabulary.RDFS_LABEL.getIRI(),
    IRI.create("http://www.w3.org/2004/02/skos/core#prefLabel")
]
```

---

### subClassOf 계층 탐색

클래스: `AssertedClassHierarchyProvider`

```java
// 부모 탐색: 해당 클래스가 주어인 axiom 순회
for (OWLAxiom ax : ont.getAxioms(cls, Imports.EXCLUDED)) {
    ax.accept(parentClassExtractor);  // SubClassOfAxiom, EquivalentClassesAxiom 처리
}

// 자식 탐색: 역방향 — 해당 클래스를 참조하는 axiom 역조회
for (OWLAxiom ax : ont.getReferencingAxioms(parent)) {
    ax.accept(childClassExtractor);
}
```

`AbstractOWLObjectHierarchyProvider`에서 재귀 탐색(사이클 방지 포함)으로 전체 ancestor/descendant 집합 구성.

---

### Named Graph / Import 처리

- `owl:imports` 선언된 온톨로지를 **자동으로 모두 로드** (imports closure)
- `getActiveOntologies()` = 현재 온톨로지 + import된 모든 온톨로지
- 실패한 import는 `MissingImportHandlingStrategy.SILENT`로 무시
- Named Graph는 별도 `OWLOntology` 객체로 표현, `Imports.EXCLUDED` 플래그로 독립 조회 가능

로딩 흐름:
```
OntologyLoader (비동기, EDT 외)
  └─ IRI 매퍼 체인: UserResolved → WebConnection → AutoMappedRepository(catalog.xml)
  └─ 임시 매니저 로딩 후 메인 매니저로 MOVE
  └─ getImportsClosure() 전체 포맷 업데이트
```

---

### 우리 백엔드와 비교

| | Protege | 우리 백엔드 |
|---|---|---|
| 클래스 탐색 | `getClassesInSignature()` (인메모리 Java) | SPARQL 5가지 패턴 (`owl:Class`, `rdfs:Class`, `skos:Concept` 등) |
| 레이블 | `getAnnotationAssertionAxioms()` + Visitor | SPARQL `OPTIONAL { ?iri rdfs:label ?label }` |
| 계층 | `getAxioms(cls)` + Visitor 역방향 탐색 | SPARQL `rdfs:subClassOf` |
| Import | imports closure 자동 포함 | Named Graph 필터로 선택적 조회 |

