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
