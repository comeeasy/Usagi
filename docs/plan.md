# 기획서: Palantir Foundry 온톨로지 플랫폼

**작성일:** 2026-03-23
**버전:** 1.2

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

## 4. 저장소 아키텍처: RDF vs LPG 검토

### RDF Triplestore vs LPG 핵심 비교

| 비교 항목 | RDF/OWL Triplestore | LPG (Neo4j 등) |
|-----------|---------------------|----------------|
| **데이터 단위** | Triple (S-P-O) | Node + Edge + Properties |
| **OWL 추론** | 내장 (HermiT, Pellet) | 없음 (외부 연동 필요) |
| **쿼리 언어** | SPARQL (W3C 표준) | Cypher / GQL (ISO 2024) |
| **그래프 탐색 성능** | 느림 (triple join 비용) | 빠름 (pointer-based traversal) |
| **엣지 속성** | 불가 (RDF-star로 부분 해결) | 기본 지원 |
| **표준 상호운용** | 높음 (W3C Linked Data) | 낮음 (벤더별 상이) |
| **외부 온톨로지 Import** | 직접 지원 | n10s(neosemantics)로 부분 지원 |
| **GraphRAG/LLM 통합** | 어려움 (SPARQL 복잡) | 우수 (Cypher가 LLM 친화적) |

### LPG 단독 사용의 한계 (우리 요구사항 기준)

neosemantics(n10s, Neo4j Labs 공식 플러그인)로 RDF/OWL을 LPG에 import할 수 있으나:
- OWL 2 DL 추론 **미지원** — cardinality, transitive/symmetric property, complex class expression 등 silently 무시
- SPARQL 엔드포인트 **없음** (GitHub Issue #193, 구현 계획 없음)
- `owl:Restriction` 등 복잡한 OWL 구조 로딩 **불완전**
- Neo4j Labs 프로젝트 — 프로덕션 SLA 보장 없음

→ **OWL 추론 + 표준 온톨로지 Import가 Must Have인 이 프로젝트에서 LPG 단독은 부적합**

### 채택 아키텍처: Hybrid (RDF 추론 + LPG 탐색)

```
[OWL 온톨로지 정의]
        |
        v
[RDF Triplestore (Oxigraph)]  ←── SPARQL 에디터
        |
   OWL Reasoner (owlready2)
        |
   추론된 triple 포함 전체 그래프
        |
        | ETL / 동기화 (비동기 백그라운드)
        v
[Neo4j LPG]  ←── Cytoscape.js 그래프 시각화
                  GraphRAG / MCP 탐색 질의 (Cypher)
                  GDS 알고리즘 (PageRank, community detection)
```

**RDF store 역할:** 온톨로지 진실 원본(source of truth), OWL 추론, SPARQL, 표준 Import/Export
**LPG 역할:** 고속 서브그래프 탐색, AI Agent 질의(Cypher가 SPARQL보다 LLM 친화적), 그래프 시각화 데이터 제공

### Palantir Foundry의 접근 방식 (참고)

Foundry는 RDF/OWL도, 순수 LPG도 아닌 독자적 "Operational Ontology" 레이어를 사용한다:
- Object Type (≈ owl:Class), Link Type (≈ ObjectProperty), Property (≈ DataProperty)
- **핵심 원칙: "Object Type Backing"** — Foundry 데이터셋의 각 row가 하나의 Individual(Object)가 됨. 열이 Property로 매핑됨.
- Object Storage V2(OSv2): Funnel(쓰기 오케스트레이션) + OSS(읽기 서빙) 분리 → CQRS 패턴. Object Type 당 수백억 객체 지원.
- Multi-Datasource Object Type(MDO): 복수 소스를 PK 기준으로 Column-wise Join하여 하나의 Object Type에 연결.
- 내부 저장 기술은 비공개; W3C 비표준 — SPARQL, IRI, Linked Data 연계 없음
- **우리 프로젝트는 Foundry의 Backing/MDO/Funnel 개념을 참조하되 W3C 표준 호환성을 유지하는 방향으로 차별화**

---

## 5. 다중 소스 Individual 수집 아키텍처

### 핵심 문제: 소스가 다른 Individual을 어떻게 하나의 Concept에 연결하는가?

Foundry의 MDO(Multi-Datasource Object Type) 개념을 W3C OWL/RDF로 구현한다.
각 Individual은 하나 이상의 **Backing Source**에서 비롯되며, 공통 Primary Key(IRI)를 통해 동일 Concept 인스턴스로 통합된다.

```
Concept: ex:Employee (OWL Class)
    ├── Backing Source A: JDBC (HR 시스템 RDB)
    │     row [emp_id=42, name="Alice"] → ex:employee/42 rdf:type ex:Employee
    │
    ├── Backing Source B: API Stream (근태 시스템)
    │     event {emp_id: 42, checkin: "09:00"} → ex:employee/42 ex:lastCheckin "09:00"
    │
    └── Backing Source C: 수동 입력
          triple {ex:employee/42 ex:role "Manager"} → ex:employee/42 ex:role "Manager"

→ 최종: ex:employee/42 가 세 소스의 Property를 모두 보유한 단일 Individual
```

### IRI 생성 전략 (소스별)

| 소스 유형 | IRI 생성 방법 | 예시 |
|-----------|--------------|------|
| RDB (JDBC) | `{base}/{table}/{PK}` | `ex:employee/42` |
| API Stream | `{base}/{entity_type}/{source_id}` | `ex:sensor/device-001` |
| 수동 입력 | 사용자 지정 IRI 또는 UUID 자동 생성 | `ex:person/uuid-...` |
| 표준 온톨로지 Import | 원본 IRI 유지 | `schema:Person` |

**교차 소스 deduplication 원칙:**
- 동일 IRI = 동일 Individual → Property는 union으로 합산 (Foundry Column-wise MDO)
- 소스 간 동일 IRI에 충돌 Property가 있을 때: "사용자 편집 우선" 또는 "최신 값 우선" 정책 중 선택
- 소스 식별자가 달라서 fuzzy match가 필요한 경우: Entity Resolution 레이어 (향후 확장)

### 고처리량 수집 아키텍처 (CQRS + Event Sourcing)

```
┌─────────────────────────────────────────────────────────────┐
│                      WRITE PATH                              │
│                                                             │
│  [RDB/JDBC]──────┐                                          │
│  [API Stream]────┤→ [Kafka Topic: raw-source-events]        │
│  [수동 입력]──────┤     ↓                                    │
│                  │  [Ingestion Service (FastAPI Worker)]    │
│                  │  - IRI 생성 (소스별 템플릿)               │
│                  │  - Concept 매핑 (Backing Source 설정)    │
│                  │  - RDF Triple 직렬화                     │
│                  │     ↓                                    │
│                  └→ [Kafka Topic: rdf-triples]              │
│                          ↓                                  │
│              [Oxigraph (Triple Store)]                      │
│              SPARQL Update (batch 또는 streaming)           │
└─────────────────────────────────────────────────────────────┘
              ↓  비동기 동기화 (Kafka Consumer)
┌─────────────────────────────────────────────────────────────┐
│                      READ PATH                               │
│                                                             │
│              [Neo4j LPG]                                    │
│              ← Cytoscape.js 그래프 시각화                   │
│              ← MCP Cypher 탐색 질의                         │
│              ← AI Agent GraphRAG                            │
└─────────────────────────────────────────────────────────────┘
```

**소스 유형별 수집 방법:**

| 소스 유형 | 수집 방법 | 지연 | 비고 |
|-----------|----------|------|------|
| RDB (분석용, 읽기 전용) | **Ontop Virtual KG** (SPARQL→SQL 실시간 재작성) | 즉시 | Triple 복제 없음, 원본 RDB가 최적화된 경우 적합 |
| RDB (ETL 필요) | **R2RML/RML Mapper** → Triple Store 적재 | 배치 (분~시간) | 복잡한 추론, 다중 소스 통합 시 |
| REST API (배치) | Kafka Connect HTTP Source → Ingestion Worker | 분~시간 | 스케줄 기반 |
| REST API (스트리밍) | Kafka Producer → Ingestion Worker → RDF 변환 | 초~분 | 실시간 이벤트 |
| 사용자 수동 입력 | SPARQL Update 직접 호출 (즉시) | 즉시 | 단건 트랜잭션 |
| OWL 파일 Import | rdflib 파싱 → Oxigraph bulk insert | 1회성 | TBox + ABox 모두 포함 |

### Individual Provenance 메타데이터

모든 Individual은 Named Graph를 통해 소스 추적 가능:
```turtle
# Named Graph = 수집 트랜잭션 단위
GRAPH ex:source/jdbc-hr/2026-03-23T09:00:00 {
    ex:employee/42 rdf:type ex:Employee ;
                   ex:name "Alice" .
}
GRAPH ex:source/api-stream/attendance/2026-03-23T09:05:00 {
    ex:employee/42 ex:lastCheckin "09:00" .
}
```
- Named Graph IRI = `{source_type}/{source_id}/{timestamp}`
- Provenance 메타데이터: `prov:wasGeneratedBy`, `prov:generatedAtTime`, `dcterms:source`
- 소스별 Triple 삭제/롤백 시 Named Graph 단위로 제거 가능

---

## 6. 기술 스택 제안 및 근거

### Backend
| 선택 | 근거 |
|------|------|
| **Python + FastAPI** | rdflib, owlready2 등 SemanticWeb 생태계가 Python에 집중. 비동기 REST 지원 |
| **Oxigraph** (RDF 저장소) | Rust 기반 고성능 SPARQL 1.1 엔드포인트. Named Graph 지원. in-process Python 바인딩. 진실 원본 |
| **owlready2** (Reasoner) | HermiT 기반 OWL 2 추론기 내장, Python에서 직접 호출 가능 |
| **Neo4j** (LPG, 탐색 레이어) | 고속 서브그래프 탐색, Cypher 질의, GDS 알고리즘, LLM/MCP 친화적 |
| **Kafka** (메시지 큐) | 고처리량 수집 이벤트 버퍼링, 소스별 토픽 분리, Exactly-once 보장 |
| **Ontop** (Virtual KG, 선택적) | RDB → SPARQL 실시간 재작성. ETL 없이 RDB Individual을 온톨로지에 노출 |

### Frontend
| 선택 | 근거 |
|------|------|
| **React + TypeScript** | 컴포넌트 재사용, 타입 안전성 |
| **Cytoscape.js** | 온톨로지 그래프 시각화에 특화된 라이브러리 (클러스터, 레이아웃 풍부) |
| **SPARQL 에디터** | CodeMirror + SPARQL 언어 플러그인 |
| **TailwindCSS** | 빠른 UI 구성 |

### MCP 인터페이스
| 선택 | 근거 |
|------|------|
| **FastMCP (Python)** | MCP 서버를 FastAPI와 함께 단일 프로세스로 운영 가능 |

### 인프라
- **Docker Compose**: Backend + Frontend + Oxigraph + Neo4j + Kafka 컨테이너 구성
- **Nginx**: 리버스 프록시 (Frontend SPA + API 라우팅)

---

## 7. 페이지 구성 (사이트맵)

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

## 8. MCP 도구 목록 (AI Agent용)

AI Agent가 MCP를 통해 사용할 수 있는 도구:

| 도구 | 설명 |
|------|------|
| `search_entities` | 이름/타입 기반 Entity 검색 |
| `search_relations` | 도메인/레인지/타입 기반 Relation 검색 |
| `get_subgraph` | 지정 Entity 집합의 서브그래프 반환 |
| `sparql_query` | SPARQL SELECT/ASK 실행 |
| `get_ontology_summary` | 온톨로지 통계 요약 |
| `list_ontologies` | 사용 가능한 온톨로지 목록 |
| `run_reasoner` | 서브그래프 정합성 검증 실행 |

---

## 9. 표준 온톨로지 Import 지원 형식

- **파일 업로드**: `.owl`, `.ttl` (Turtle), `.rdf` (RDF/XML), `.jsonld` (JSON-LD), `.n3`
- **URL 직접 Import**: HTTP로 공개된 온톨로지 URL 입력
- **사전 등록 온톨로지**: schema.org, FOAF, Dublin Core, OWL, RDFS, SKOS 원클릭 Import

---

## 10. 온톨로지 Merge 정책

병합 시 IRI 충돌 처리 전략:
1. **자동 병합**: 동일 IRI는 속성을 union으로 합침
2. **충돌 감지**: 동일 IRI에 상충되는 domain/range 정의가 있으면 사용자에게 선택 요청
3. **Prefix 분리**: 충돌 방지를 위해 소스 온톨로지 prefix를 네임스페이스에 반영

---

## 11. 레퍼런스 및 디자인 방향

**레퍼런스:**
- Palantir Foundry Ontology Manager UI
- Protégé (데스크탑 온톨로지 에디터)
- GraphDB Workbench

**디자인 방향:**
- Foundry 스타일: 다크 사이드바 + 밝은 메인 콘텐츠 영역
- 그래프 뷰 중심: 온톨로지를 시각적으로 탐색하는 것이 주된 UX
- 정보 밀도 높은 테이블/패널 (엔터프라이즈 툴 감성)

---

## 12. 활용 가능한 오픈소스 라이브러리

| 라이브러리 | 용도 | 레이어 | 라이선스 |
|-----------|------|--------|---------|
| [rdflib](https://github.com/RDFLib/rdflib) | RDF 파싱·직렬화·SPARQL | RDF | BSD |
| [owlready2](https://github.com/pwin/owlready2) | OWL 온톨로지 + HermiT 추론기 | RDF | LGPL |
| [oxigraph](https://github.com/oxigraph/oxigraph) | 고성능 RDF 저장소 + SPARQL 1.1 + Named Graph | RDF | MIT/Apache |
| [ontop](https://github.com/ontop/ontop) | Virtual KG: SPARQL→SQL, RDB→온톨로지 노출 | Ingestion | Apache 2.0 |
| [kafka-python](https://github.com/dpkp/kafka-python) | Kafka Producer/Consumer (수집 파이프라인) | Ingestion | Apache 2.0 |
| [neo4j-driver (Python)](https://github.com/neo4j/neo4j-python-driver) | Neo4j LPG 연결 및 Cypher 질의 | LPG | Apache 2.0 |
| [fastmcp](https://github.com/jlowin/fastmcp) | MCP 서버 구축 | MCP | MIT |
| [cytoscape.js](https://js.cytoscape.org/) | 그래프 시각화 | Frontend | MIT |
| [codemirror](https://codemirror.net/) | SPARQL 에디터 | Frontend | MIT |
| [FastAPI](https://fastapi.tiangolo.com/) | REST API 서버 | Backend | MIT |
