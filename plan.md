# Neo4j + Oxigraph → Apache Jena Fuseki 마이그레이션 계획

## 배경

현재 프로젝트는 RDF/OWL(Oxigraph)과 LPG(Neo4j)의 하이브리드 구조로 설계되어 있다.
Neo4j Community Edition은 상업적 사용 시 라이선스 비용이 발생하며, Oxigraph와의 이중 저장소 구조는
동기화 복잡성을 야기한다.

**목표:** 두 저장소를 모두 제거하고, 오픈소스 Apache Jena Fuseki(SPARQL 서버)로 단일화한다.

## 확정 아키텍처

```
Before:  FastAPI → pyoxigraph(Oxigraph) + neo4j driver(Neo4j) + SyncService
After:   FastAPI → httpx → Jena Fuseki (TDB2, Named Graph 지원)
```

- **제거:** Neo4j (LPG), Oxigraph (embedded RDF store), SyncService
- **추가:** Apache Jena Fuseki (Docker, TDB2 persistent store)
- **Python ↔ Fuseki 통신:** `httpx` (기존 의존성) via HTTP SPARQL Protocol

## 브랜치

`feat/replace-neo4j-with-jena`

---

## 변경 파일 목록

### 삭제 (3개)

| 파일 | 이유 |
|------|------|
| `backend/services/graph_store.py` | Neo4j AsyncDriver 래퍼 전체 |
| `backend/services/sync_service.py` | Oxigraph → Neo4j 동기화 서비스 불필요 |
| `backend/workers/sync_worker.py` | 동기화 워커 불필요 |

### 전면 재작성 (2개)

| 파일 | 변경 내용 |
|------|---------|
| `backend/services/ontology_store.py` | `pyoxigraph` 제거 → `httpx` 기반 Fuseki HTTP 클라이언트로 대체. `Triple` 타입을 rdflib 기반으로 변경. SPARQL Query/Update/GSP 엔드포인트 사용 |
| `backend/services/import_service.py` | `pyoxigraph` 제거, `rdflib`으로 모든 포맷(Turtle/RDF-XML/JSON-LD/N3/NT) 파싱 통일 |

### 부분 수정 (11개)

| 파일 | 변경 내용 |
|------|---------|
| `backend/config.py` | `neo4j_*`, `oxigraph_path`, `sync_*` 설정 제거 → `fuseki_url`, `fuseki_dataset` 추가 |
| `backend/requirements.txt` | `neo4j==5.23.0`, `pyoxigraph==0.4.0` 제거 |
| `backend/docker-compose.yml` | `neo4j` 서비스 제거, `oxigraph-data` 볼륨 제거, Jena Fuseki 서비스 추가 |
| `backend/main.py` | `GraphStore` 초기화/종료 제거, `sync_worker` import/태스크 제거, `OntologyStore` 생성자 변경 |
| `backend/api/ontologies.py` | `graph_store` 의존성 제거, `POST /{id}/sync` 엔드포인트 제거, `delete_ontology_data()` 호출 제거 |
| `backend/api/individuals.py` | `graph_store.upsert_individual`, `upsert_object_property_value`, `sync_object_property_values`, `delete_node` 호출 제거 |
| `backend/api/subgraph.py` | Neo4j Cypher BFS → SPARQL 반복 확장(iterative BFS via SPARQL SELECT + VALUES) 으로 대체 |
| `backend/api/sources.py` | `CSVImporter(store, graph_store)` → `CSVImporter(store)` 로 변경 |
| `backend/services/ingestion/csv_importer.py` | Phase 2 (Neo4j UNWIND 배치) 제거. Phase 1 pyoxigraph 내부 직접 접근(`_store.extend`) → `OntologyStore.insert_triples()` 사용으로 변경 |
| `backend/services/reasoner_service.py` | `from pyoxigraph import NamedNode` 제거 → `rdflib.URIRef` 사용으로 교체 |
| `backend/app_mcp/tools.py` | `init_services()`에서 `graph_store` 파라미터 제거, `add_individual` / `update_individual` / `delete_individual` / `add_concept` 내 Neo4j 동기화 호출 제거 |

---

## Jena Fuseki Docker 구성

```yaml
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

---

## 서브그래프 쿼리 교체 전략

Neo4j Cypher BFS → Python-side iterative SPARQL BFS

```
1. seed_iris를 초기 frontier로 설정
2. depth 횟수만큼 반복:
   a. frontier의 모든 IRI에서 직/역방향 이웃 IRI를 SPARQL SELECT로 조회
   b. 새 IRI를 visited에 추가, frontier 갱신
   c. 총 노드 수가 500 초과 시 중단
3. visited IRI들의 타입/레이블을 SPARQL 일괄 조회
4. visited IRI들 사이의 엣지를 SPARQL 청크(30개씩) 조회
5. {nodes: [...], edges: [...]} 반환
```

---

## 진행 상태

- [x] 브랜치 생성: `feat/replace-neo4j-with-jena`
- [x] 계획 수립 및 문서화 (plan.md)
- [x] Step 1: 설정/의존성 변경 (config.py, requirements.txt, docker-compose.yml)
- [x] Step 2: ontology_store.py 재작성 (Fuseki HTTP 클라이언트)
- [x] Step 3: import_service.py 재작성 (rdflib 통일)
- [x] Step 4: csv_importer.py 수정 (Phase 2 제거)
- [x] Step 5: reasoner_service.py 수정 (pyoxigraph 제거)
- [x] Step 6: main.py 수정
- [x] Step 7: API 수정 (ontologies, concepts, individuals, subgraph, sources)
- [x] Step 8: app_mcp/tools.py 수정
- [x] Step 9: 삭제 파일 제거 (graph_store, sync_service, sync_worker)
- [x] 테스트 수정 (conftest, test_mcp_tools, test_service_*)

---

## Multi-Dataset 지원 계획 (Option B: Dataset Pool)

### 배경

현재 Fuseki dataset이 앱 시작 시 단일 값으로 고정된다.
사용자가 런타임에 여러 dataset을 동시에 사용할 수 있어야 한다.

### 설계 원칙

- **OntologyStore 싱글톤 유지** — 하나의 인스턴스가 내부 httpx 클라이언트(연결 풀)를 보유
- **dataset은 메서드 파라미터로 전달** — URL을 호출 시점에 동적으로 조립
- **기본값 "ontology" 유지** — 하위 호환성 보장, 기존 클라이언트 수정 불필요
- **프론트엔드 dataset 선택 UI** — Sidebar에 DatasetSelector 추가, React Context로 전파

### 확정 아키텍처

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

### 데이터 흐름

```
사용자가 Sidebar에서 "dataset-B" 선택
  → DatasetContext 업데이트
    → API 호출: GET /concepts?dataset=dataset-B
      → FastAPI: dataset="dataset-B" 추출
        → store.sparql_select(query, dataset="dataset-B")
          → POST http://fuseki:3030/dataset-B/sparql
```

---

### 변경 범위

#### 백엔드 (3개 파일, ~200줄)

| 파일 | 변경 내용 |
|------|---------|
| `backend/services/ontology_store.py` | 모든 public 메서드에 `dataset: str \| None = None` 파라미터 추가. 내부 URL을 `{fuseki_base}/{dataset or default}/sparql` 형태로 동적 조립. `fuseki_base_url`, `default_dataset` 속성 분리. |
| `backend/api/*.py` (11개 파일) | 모든 엔드포인트에 `dataset: str = Query("ontology")` 추가. store 호출 시 dataset 전달. |
| `backend/app_mcp/tools.py` | 11개 MCP 도구에 `dataset: str = "ontology"` 파라미터 추가. store 메서드 호출 시 dataset 전달. |

**OntologyStore 변경 전/후:**
```python
# Before
class OntologyStore:
    def __init__(self, fuseki_url: str, dataset: str = "ontology"):
        self._query_url = f"{fuseki_url}/{dataset}/sparql"
    
    async def sparql_select(self, query: str) -> list[dict]:
        resp = await self._client.post(self._query_url, ...)

# After
class OntologyStore:
    def __init__(self, fuseki_url: str, dataset: str = "ontology"):
        self._fuseki_base = fuseki_url
        self._default_dataset = dataset
    
    def _query_url(self, dataset: str) -> str:
        return f"{self._fuseki_base}/{dataset}/sparql"
    
    async def sparql_select(self, query: str, dataset: str | None = None) -> list[dict]:
        url = self._query_url(dataset or self._default_dataset)
        resp = await self._client.post(url, ...)
```

**API 엔드포인트 변경 전/후:**
```python
# Before
@router.get("")
async def list_concepts(request: Request, ontology_id: str, ...):
    store = request.app.state.ontology_store
    rows = await store.sparql_select(query)

# After
@router.get("")
async def list_concepts(
    request: Request,
    ontology_id: str,
    dataset: str = Query("ontology"),  # ← 추가
    ...
):
    store = request.app.state.ontology_store
    rows = await store.sparql_select(query, dataset=dataset)  # ← dataset 전달
```

---

#### 프론트엔드 (~600줄)

##### 신규 파일 (2개)

| 파일 | 내용 |
|------|------|
| `frontend/src/contexts/DatasetContext.tsx` | 현재 선택된 dataset 상태를 앱 전체에 공유하는 React Context + Provider. `activeDataset`, `setActiveDataset` 노출. |
| `frontend/src/components/layout/DatasetSelector.tsx` | Sidebar에 삽입할 드롭다운 컴포넌트. 백엔드 `/api/v1/datasets` 엔드포인트 또는 환경 설정에서 목록 조회. |

##### 수정 파일

| 파일 | 변경 내용 |
|------|---------|
| `frontend/src/api/ontologies.ts` | 모든 API 함수에 `dataset?: string` 파라미터 추가. 쿼리스트링에 자동 포함. |
| `frontend/src/api/entities.ts` | `listConcepts`, `listIndividuals`, `searchEntities` 등에 `dataset` 추가. |
| `frontend/src/api/relations.ts` | `listObjectProperties`, `listDataProperties` 등에 `dataset` 추가. |
| `frontend/src/api/reasoner.ts` | `runReasoner`, `getReasonerResult`에 `dataset` 추가. |
| `frontend/src/api/sparql.ts` | `executeSparql`에 `dataset` 추가. |
| `frontend/src/api/sources.ts` | 모든 source 관련 함수에 `dataset` 추가. |
| `frontend/src/hooks/useOntology.ts` 등 | React Query `queryKey`에 `dataset` 포함. DatasetContext에서 자동으로 주입. |
| `frontend/src/components/layout/Sidebar.tsx` | DatasetSelector 컴포넌트 삽입. |
| `frontend/src/App.tsx` 또는 최상위 | DatasetContext.Provider로 감싸기. |

---

#### 추가 고려사항

**dataset 목록 조회 API (선택)**
프론트엔드에서 사용 가능한 dataset 목록을 표시하려면 백엔드에 엔드포인트 추가 필요:
```
GET /api/v1/datasets
→ Fuseki Admin API (GET http://fuseki:3030/$/datasets) 호출 후 목록 반환
```

**URL 상태 동기화 (선택)**
dataset 선택을 URL 쿼리스트링(`?dataset=xxx`)에도 반영하면
북마크/공유 가능한 링크 생성 및 새로고침 시 선택 유지 가능.

---

### 변경 규모 요약

| 영역 | 파일 수 | 예상 변경 라인 |
|------|--------|--------------|
| 백엔드 OntologyStore | 1 | ~60 |
| 백엔드 API (11개) | 11 | ~150 |
| 백엔드 MCP Tools | 1 | ~100 |
| 프론트엔드 API 클라이언트 | 6 | ~120 |
| 프론트엔드 Context/Hook | 2 | ~120 |
| 프론트엔드 컴포넌트 (신규+수정) | 3 | ~150 |
| **합계** | **~24** | **~700** |

---

### 진행 상태

- [x] Multi-Step 1: OntologyStore 메서드 dataset 파라미터화
- [x] Multi-Step 2: 백엔드 API 11개 엔드포인트 dataset Query param 추가
- [x] Multi-Step 3: MCP Tools dataset 파라미터 추가
- [x] Multi-Step 4: 백엔드 `/api/v1/datasets` 엔드포인트 추가 (선택)
- [x] Multi-Step 5: 프론트엔드 DatasetContext 추가
- [x] Multi-Step 6: 프론트엔드 API 클라이언트 dataset 파라미터 추가
- [x] Multi-Step 7: DatasetSelector 컴포넌트 구현 + Sidebar 통합

---

## Entity / Relation 조회 불가 + 레이턴시 수정 계획

### 현황 파악 (코드 기준)

모든 쓰기/읽기 경로의 실제 그래프 사용 현황:

| 경로 | 저장 그래프 | 읽기 가능? |
|------|-----------|-----------|
| `import_file/url/standard` | `{ontology_iri}/kg` | ✅ |
| `api/concepts` CRUD | `{ontology_iri}/kg` | ✅ |
| `api/individuals` CRUD | `{ontology_iri}/kg` | ✅ |
| `api/properties` CRUD | `{ontology_iri}/kg` | ✅ |
| CSV importer | `{ontology_iri}/kg` | ✅ (이미 올바름) |
| **MCP `add_individual`** | `urn:source:manual/{ontology_id}` | ❌ |
| **MCP `add_concept`** | `{ontology_id}/tbox` | ❌ |
| **MCP `update_individual`** | `urn:source:manual/{ontology_id}` | ❌ |

> CSV importer는 `resolve_kg_graph_iri()`를 통해 이미 `{ontology_iri}/kg`에 씁니다.
> 문제는 **MCP tools만** 다른 그래프에 씁니다.

---

### 전략: 단일 Named Graph `{ontology_iri}/kg`으로 통일

모든 쓰기가 `{ontology_iri}/kg`에 들어가면, 기존 읽기 쿼리(`GRAPH <{kg}>`) 그대로 작동합니다.
프로비넌스는 그래프 분리 대신 트리플 속성(`prov:wasAttributedTo`, `prov:generatedAtTime`)으로 기록합니다.

> **MCP에서 `ontology_id`는 UUID가 아니라 온톨로지 IRI 전체 문자열입니다.**
> `kg_graph_iri("https://infiniq.co.kr/jc3iedm/")` = `"https://infiniq.co.kr/jc3iedm/kg"` ✅

---

### 단계별 작업

#### Fix-1: MCP tools — 그래프 통일

**파일**: `backend/app_mcp/tools.py`

`_manual_graph()` 헬퍼 함수 삭제. `kg_graph_iri()` import 후 사용.

```python
# Before
def _manual_graph(ontology_id: str) -> str:
    return f"urn:source:manual/{ontology_id}"

graph_iri = _manual_graph(ontology_id)        # add_individual
tbox_graph = f"{ontology_id}/tbox"            # add_concept
g = _manual_graph(ontology_id)                # update_individual

# After
from services.ontology_graph import kg_graph_iri

graph_iri = kg_graph_iri(ontology_id)         # add_individual
tbox_graph = kg_graph_iri(ontology_id)        # add_concept
g = kg_graph_iri(ontology_id)                 # update_individual
```

주의: `delete_individual`은 `GRAPH ?g { ... }` 패턴으로 전체 그래프 탐색을 하므로 변경 불필요.

- [ ] Fix-1-a: `_manual_graph` 헬퍼 삭제
- [ ] Fix-1-b: `add_individual` — `graph_iri = kg_graph_iri(ontology_id)`
- [ ] Fix-1-c: `add_concept` — `tbox_graph = kg_graph_iri(ontology_id)`
- [ ] Fix-1-d: `update_individual` — `g = kg_graph_iri(ontology_id)`

---

#### Fix-2: Individual 판별 패턴 — GRAPH 절 누락 수정

**파일**: `backend/api/individuals.py`, `backend/api/search.py`

`_individual_pattern(kg)` 내 두 번째 UNION 브랜치의 `?ctype a owl:Class` 체크가 GRAPH 절 없이 실행되어, Fuseki default graph(비어 있음)를 보므로 항상 빈 결과가 됩니다.

```sparql
-- Before (GRAPH 절 없음 → default graph 조회 → 빈 결과)
{ ?ctype a owl:Class }
UNION
{ ?ctype a rdfs:Class . FILTER NOT EXISTS { ?ctype a owl:Ontology } }

-- After (같은 kg 그래프 안에서 체크)
{ GRAPH <{kg}> { ?ctype a owl:Class } }
UNION
{ GRAPH <{kg}> { ?ctype a rdfs:Class . FILTER NOT EXISTS { ?ctype a owl:Ontology } } }
```

`get_concept()`의 `individual_count` 쿼리도 같은 문제:

```sparql
-- Before
SELECT (COUNT(DISTINCT ?ind) AS ?cnt) WHERE { ?ind rdf:type <{iri}> }

-- After
SELECT (COUNT(DISTINCT ?ind) AS ?cnt) WHERE {
    GRAPH <{kg}> { ?ind rdf:type <{iri}> }
}
```

- [x] Fix-2-a: `individuals.py` `_individual_pattern()` — ctype 체크에 `GRAPH <{kg}>` 추가
- [x] Fix-2-b: `search.py` `_ind_pat` 인라인 패턴 — 동일 수정
- [x] Fix-2-c: `concepts.py` `get_concept()` — `individual_count` 쿼리 GRAPH 절 추가

---

#### Fix-3: search_relations() N+1 쿼리 제거

**파일**: `backend/api/search.py`

현재 property N개에 대해 각각 domain + range를 별도 조회 → **N×2개 추가 왕복**.
`GROUP_CONCAT`으로 메인 쿼리에서 한 번에 가져옵니다.

```sparql
-- Before: rows 루프에서 domain_rows, range_rows 각각 await

-- After: 단일 쿼리
SELECT ?iri ?label ?kind
       (GROUP_CONCAT(DISTINCT STR(?domain); SEPARATOR="\t") AS ?domains)
       (GROUP_CONCAT(DISTINCT STR(?range);  SEPARATOR="\t") AS ?ranges)
WHERE {
    GRAPH <{kg}> {
        { ?iri a owl:ObjectProperty . BIND("object" AS ?kind) }
        UNION
        { ?iri a owl:DatatypeProperty . BIND("data" AS ?kind) }
        OPTIONAL { ?iri rdfs:label  ?label  }
        OPTIONAL { ?iri rdfs:domain ?domain }
        OPTIONAL { ?iri rdfs:range  ?range  }
        {q_filter}
        {domain_filter}
        {range_filter}
    }
} GROUP BY ?iri ?label ?kind
ORDER BY ?label LIMIT {limit}
```

파싱: `?domains` 문자열을 `"\t"` 기준으로 `split()` → `list[str]`.

- [x] Fix-3: `search_relations()` — GROUP_CONCAT 단일 쿼리로 교체

---

#### Fix-4: get_concept() 순차 쿼리 → 병렬화

**파일**: `backend/api/concepts.py`

현재 6개 쿼리 순차 실행 → `asyncio.gather`로 동시 실행:

```python
import asyncio

basic, sc_rows, ec_rows, dw_rows, rest_rows, cnt_rows = await asyncio.gather(
    store.sparql_select(basic_q, dataset=dataset),
    store.sparql_select(sc_q,    dataset=dataset),
    store.sparql_select(ec_q,    dataset=dataset),
    store.sparql_select(dw_q,    dataset=dataset),
    store.sparql_select(rest_q,  dataset=dataset),
    store.sparql_select(cnt_q,   dataset=dataset),
)
```

- [x] Fix-4: `get_concept()` — asyncio.gather 병렬화

---

### 변경 파일 요약

| Fix | 파일 | 변경 내용 |
|-----|------|---------|
| Fix-1 | `app_mcp/tools.py` | `_manual_graph` 삭제, `kg_graph_iri` 사용 |
| Fix-2-a | `api/individuals.py` | `_individual_pattern()` GRAPH 절 추가 |
| Fix-2-b | `api/search.py` | `_ind_pat` GRAPH 절 추가 |
| Fix-2-c | `api/concepts.py` | `individual_count` 쿼리 GRAPH 절 추가 |
| Fix-3 | `api/search.py` | `search_relations()` GROUP_CONCAT 단일 쿼리 |
| Fix-4 | `api/concepts.py` | `get_concept()` asyncio.gather |

### 진행 상태

- [ ] Fix-1: MCP tools 그래프 통일 (`kg_graph_iri`) — 추후 테스트 후 진행
- [x] Fix-2: Individual 판별 패턴 GRAPH 절 명시 (3곳)
- [x] Fix-3: search_relations() GROUP_CONCAT 단일 쿼리
- [x] Fix-4: get_concept() asyncio.gather 병렬화
