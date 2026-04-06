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
- [ ] Step 1: 설정/의존성 변경 (config.py, requirements.txt, docker-compose.yml)
- [ ] Step 2: ontology_store.py 재작성 (Fuseki HTTP 클라이언트)
- [ ] Step 3: import_service.py 재작성 (rdflib 통일)
- [ ] Step 4: csv_importer.py 수정 (Phase 2 제거)
- [ ] Step 5: reasoner_service.py 수정 (pyoxigraph 제거)
- [ ] Step 6: main.py 수정
- [ ] Step 7: API 수정 (ontologies, individuals, subgraph, sources)
- [ ] Step 8: app_mcp/tools.py 수정
- [ ] Step 9: 삭제 파일 제거 (graph_store, sync_service, sync_worker)
