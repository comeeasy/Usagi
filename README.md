# Ontology Platform

Palantir Foundry 스타일의 온톨로지 관리 플랫폼.
OWL 2 온톨로지 편집, RDF 트리플 스토어, 그래프 시각화, SPARQL 에디터, OWL 추론기, MCP 연동을 제공합니다.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS v4, Cytoscape.js, CodeMirror 6 |
| Backend | FastAPI, Python 3.12, pyoxigraph, rdflib, owlready2 (HermiT) |
| Graph DB | Neo4j 5 Community |
| RDF Store | Oxigraph (pyoxigraph) |
| Message Broker | Apache Kafka 3.7 |
| MCP | FastMCP |
| Reverse Proxy | Nginx |

---

## 빠른 시작

### 사전 요구사항

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2.20+

### 실행

```bash
# 저장소 클론
git clone <repo-url>
cd ontology-platform

# 전체 스택 실행
docker compose up -d

# 로그 확인
docker compose logs -f backend
```

서비스가 준비되면:

| 서비스 | URL |
|--------|-----|
| 웹 UI | http://localhost |
| Backend API | http://localhost/api/v1 |
| API 문서 (Swagger) | http://localhost:8000/docs |
| MCP 엔드포인트 | http://localhost/mcp |
| Neo4j Browser | http://localhost:7474 |

> Neo4j 초기 인증: `neo4j` / `password`

### 종료

```bash
docker compose down

# 데이터 볼륨까지 삭제
docker compose down -v
```

---

## 로컬 개발 환경

### Backend

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (선택 — 기본값으로도 동작)
cp .env.example .env  # 없으면 생략

# 개발 서버 실행 (Neo4j, Kafka 별도 실행 필요)
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
# → http://localhost:5173
```

> Vite 개발 서버는 `/api` 요청을 `http://localhost:8000` 으로 자동 프록시합니다.

---

## API 엔드포인트 요약

### 온톨로지 관리

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/ontologies` | 목록 조회 (페이지네이션) |
| `POST` | `/api/v1/ontologies` | 새 온톨로지 생성 |
| `GET` | `/api/v1/ontologies/{id}` | 상세 + 통계 |
| `PUT` | `/api/v1/ontologies/{id}` | 메타데이터 수정 |
| `DELETE` | `/api/v1/ontologies/{id}` | 삭제 (모든 Named Graph 포함) |

### 개념 (Concept / owl:Class)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/ontologies/{id}/concepts` | 목록 |
| `POST` | `/api/v1/ontologies/{id}/concepts` | 생성 |
| `GET` | `/api/v1/ontologies/{id}/concepts/{iri}` | 상세 |
| `PUT` | `/api/v1/ontologies/{id}/concepts/{iri}` | 수정 |
| `DELETE` | `/api/v1/ontologies/{id}/concepts/{iri}` | 삭제 |

### 개체 (Individual / owl:NamedIndividual)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/ontologies/{id}/individuals` | 목록 |
| `POST` | `/api/v1/ontologies/{id}/individuals` | 생성 |
| `GET` | `/api/v1/ontologies/{id}/individuals/{iri}` | 상세 |
| `GET` | `/api/v1/ontologies/{id}/individuals/{iri}/provenance` | 출처 조회 |
| `PUT` | `/api/v1/ontologies/{id}/individuals/{iri}` | 수정 |
| `DELETE` | `/api/v1/ontologies/{id}/individuals/{iri}` | 삭제 |

### 속성 (Property)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/ontologies/{id}/properties` | 목록 (object + data) |
| `POST` | `/api/v1/ontologies/{id}/properties` | 생성 |
| `GET` | `/api/v1/ontologies/{id}/properties/{iri}` | 상세 |
| `PUT` | `/api/v1/ontologies/{id}/properties/{iri}` | 수정 |
| `DELETE` | `/api/v1/ontologies/{id}/properties/{iri}` | 삭제 |

### 검색

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/ontologies/{id}/search/entities` | Entity 키워드 검색 |
| `GET` | `/api/v1/ontologies/{id}/search/relations` | Relation 검색 |

### SPARQL

```http
POST /api/v1/ontologies/{id}/sparql
Content-Type: application/json

{
  "query": "SELECT ?s ?p ?o WHERE { GRAPH <{id}/tbox> { ?s ?p ?o } } LIMIT 10"
}
```

> UPDATE/INSERT/DELETE 구문은 보안상 차단됩니다.

### 서브그래프

```http
POST /api/v1/ontologies/{id}/subgraph
Content-Type: application/json

{
  "entity_iris": ["https://example.org/Person"],
  "depth": 2
}
```

### 임포트

```http
# 파일 업로드
POST /api/v1/ontologies/{id}/import/file
Content-Type: multipart/form-data

# URL 임포트
POST /api/v1/ontologies/{id}/import/url
{ "url": "https://schema.org/version/latest/schemaorg-current-https.ttl" }

# 표준 온톨로지 (schema.org, foaf, dc, skos, owl, rdfs)
POST /api/v1/ontologies/{id}/import/standard
{ "name": "foaf" }
```

### 병합

```http
# 충돌 미리보기
POST /api/v1/ontologies/{id}/merge/preview
{ "source_ontology_id": "other-ontology-id" }

# 병합 실행
POST /api/v1/ontologies/{id}/merge
{
  "source_ontology_id": "other-ontology-id",
  "resolutions": [
    { "iri": "...", "conflict_type": "label", "choice": "keep-source" }
  ]
}
```

### 추론기 (OWL 2 HermiT)

```http
# 추론 실행 (202 Accepted + job_id 반환)
POST /api/v1/ontologies/{id}/reasoner/run
{ "subgraph_entity_iris": null }

# 결과 폴링
GET /api/v1/ontologies/{id}/reasoner/jobs/{job_id}
```

### Backing Source

```http
GET    /api/v1/ontologies/{id}/sources
POST   /api/v1/ontologies/{id}/sources
GET    /api/v1/ontologies/{id}/sources/{source_id}
PUT    /api/v1/ontologies/{id}/sources/{source_id}
DELETE /api/v1/ontologies/{id}/sources/{source_id}
POST   /api/v1/ontologies/{id}/sources/{source_id}/sync
```

---

## Named Graph 구조

온톨로지 데이터는 Oxigraph Named Graph로 분리 관리됩니다.

| Named Graph | 내용 |
|-------------|------|
| `{ontology_id}/tbox` | TBox — Class, Property 정의 (스키마) |
| `urn:source:{source_id}/{timestamp}` | ABox — Individual 데이터 (출처별) |
| `{ontology_id}/inferred` | 추론된 트리플 |

---

## MCP 연동 (AI 에이전트)

FastMCP 서버가 `/mcp` 에 마운트됩니다. Claude 등 MCP 클라이언트에서 다음 도구를 사용할 수 있습니다:

| 도구 | 설명 |
|------|------|
| `list_ontologies` | 온톨로지 목록 조회 |
| `get_ontology_summary` | 온톨로지 요약 + 통계 |
| `search_entities` | Entity 검색 (키워드) |
| `search_relations` | Relation 검색 |
| `get_subgraph` | 서브그래프 탐색 |
| `sparql_query` | SPARQL SELECT/ASK 실행 |
| `run_reasoner` | OWL 2 추론 실행 |

Claude Code에서 MCP 서버를 추가하려면:

```bash
claude mcp add ontology-platform http://localhost/mcp
```

---

## 환경 변수

Backend 컨테이너 또는 `.env` 파일에 설정합니다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j 연결 URI |
| `NEO4J_USER` | `neo4j` | Neo4j 사용자 |
| `NEO4J_PASSWORD` | `password` | Neo4j 비밀번호 |
| `KAFKA_BROKERS` | `kafka:9092` | Kafka 브로커 (콤마 구분) |
| `OXIGRAPH_PATH` | `/data/oxigraph` | Oxigraph 데이터 저장 경로 |
| `SPARQL_TIMEOUT_SECONDS` | `30` | SPARQL 쿼리 타임아웃 |
| `SYNC_INTERVAL_SECONDS` | `300` | Neo4j 동기화 주기 (초) |
| `SYNC_BATCH_SIZE` | `1000` | 동기화 배치 크기 |

---

## 테스트

```bash
cd backend

# 전체 테스트
pytest

# 특정 파일
pytest tests/test_ontologies.py -v

# 커버리지 포함
pytest --cov=. --cov-report=term-missing
```

---

## 프로젝트 구조

```
.
├── backend/
│   ├── api/              # FastAPI 라우터 (ontologies, concepts, individuals, ...)
│   ├── models/           # Pydantic 모델
│   ├── services/         # 비즈니스 로직 (OntologyStore, GraphStore, ReasonerService, ...)
│   │   └── ingestion/    # Kafka 인제스션 파이프라인
│   ├── workers/          # 백그라운드 asyncio 워커
│   ├── mcp/              # FastMCP 도구 정의
│   ├── tests/            # pytest 테스트
│   ├── main.py           # FastAPI 앱 진입점
│   ├── config.py         # pydantic-settings 설정
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # fetch 기반 API 클라이언트
│   │   ├── hooks/        # TanStack Query 훅
│   │   ├── components/   # React 컴포넌트
│   │   ├── pages/        # 페이지 컴포넌트
│   │   └── types/        # TypeScript 타입
│   ├── package.json
│   └── vite.config.ts
├── nginx/
│   └── nginx.conf        # 리버스 프록시 설정
├── docs/                 # 기획서, 설계서
└── docker-compose.yml
```
