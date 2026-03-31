# Bug 목록

## BUG-001 — Concept/Individual/Property 생성 시 네임스페이스 미자동 입력

**발견:** 시나리오 1 Step 1-2 (수동 브라우저 테스트, 2026-03-30)

**현상:** 특정 온톨로지 내에서 Concept(또는 Individual, Property)를 생성할 때 IRI 입력 필드에 해당 온톨로지의 Base IRI(네임스페이스)가 자동으로 채워지지 않음.

**기대 동작:** IRI 필드 기본값이 `{ontology.baseIri}#` 로 pre-fill되어야 함.

**현재 동작:** IRI 필드가 빈 상태로 열림 → 사용자가 전체 IRI를 직접 입력해야 함.

**수정 대상:** Concept/Individual/Property 생성 폼 컴포넌트

---

## BUG-002 — Concept 편집 UI에서 disjointWith 설정 불가

**발견:** 시나리오 3 Step 3-2 (수동 브라우저 테스트, 2026-03-30)

**현상:** Concept 생성/편집 폼에 `owl:disjointWith` 설정 필드가 없음 → SPARQL INSERT로만 설정 가능.

**기대 동작:** Concept 편집 폼에 "Disjoint With" 필드(다중 선택)가 있어야 함.

**수정 대상:** Concept 생성/편집 폼 컴포넌트 ✅ 이미 수정 완료 (ConceptForm에 disjointWith IRIListInput 존재 확인)

---

## BUG-003 — POST /subgraph 422 오류 (entity_iris required)

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** Load Graph 버튼 클릭 시 `Failed to load graph: [object Object]` 에러. 백엔드 로그에 422 Unprocessable Entity.

**원인:** `SubgraphRequest.entity_iris` 필드가 `required (min_length=1)`인데 프론트가 빈 body 전송.

**수정:** `backend/api/subgraph.py` — `entity_iris: list[str] = Field(default=[])` 로 변경. ✅ 수정 완료

---

## BUG-004 — getSubgraph 필드명/응답 구조 불일치

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** 백엔드 200 OK임에도 Cytoscape에서 "Can not create edge with unspecified source" 에러.

**원인 1:** 프론트 `getSubgraph`가 `{ rootIris, depth, includeIndividuals }` 전송 → 백엔드는 `entity_iris` 필드명 기대.

**원인 2:** 백엔드 응답이 flat `{iri, kind, ...}` 구조 → 프론트는 Cytoscape용 `{data: {id, type, ...}}` 래핑 기대.

**수정:** `frontend/src/api/ontologies.ts` — `entity_iris` 필드명 변환 + 응답 transform 추가. ✅ 수정 완료

---

## BUG-005 — Concept/Individual 삭제 시 Neo4j 미반영

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** Entities 탭에서 Concept/Individual 삭제 후 Graph 탭에서 해당 노드가 계속 표시됨.

**원인:** `delete_concept`, `delete_individual` API가 Oxigraph만 삭제하고 Neo4j `delete_node` 미호출.

**수정:** `graph_store.py` — `delete_node(iri)` 메서드 추가. `concepts.py`, `individuals.py` — delete 시 `graph_store.delete_node(iri)` 호출 추가. ✅ 수정 완료

---

## BUG-006 — 부모 Concept(superClass) Neo4j 노드에 ontologyId 미설정

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** Person의 부모 클래스(Agent 등)가 Graph에 표시되지 않음. BFS/load-all 쿼리에서 `ontologyId` 필터에 걸려 제외됨.

**원인:** `upsert_concept`이 부모 노드를 `MERGE`할 때 `ontologyId`를 설정하지 않음.

**수정:** `graph_store.py` — 부모 노드 MERGE 시 `ON CREATE SET parent.ontologyId = $ontologyId` 추가. BFS 쿼리에서 루트 노드의 `ontologyId` 필터 제거. load-all 쿼리에서 `b.ontologyId` 필터 제거. ✅ 수정 완료

---

## BUG-009 — 그래프 서브그래프에 일부 Relations(엣지)가 미표시

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** 노드는 정상 표시되나, 일부 Relations(엣지)가 나타나지 않음.

**원인 1 — Individual 수정 시 ObjectProperty 미동기화:**
`individuals.py` update 핸들러에서 `upsert_object_property_value`를 호출하지 않음 → 생성 후 편집으로 추가한 object_property_values가 Neo4j에 반영되지 않음.

**원인 2 — BFS 쿼리의 엣지 수집 범위:**
`get_subgraph`의 BFS 쿼리(`UNWIND ns + collect(node) + rs`)가 "루트 노드로부터의 경로 위에 있는 엣지"만 수집. 발견된 노드 집합 내에서 경로를 벗어난 엣지(예: depth 초과 노드 간 엣지)는 누락될 수 있음.

**원인 3 — SPARQL INSERT로 직접 추가한 트리플은 Neo4j 미반영:**
API를 거치지 않은 SPARQL INSERT의 ObjectProperty 값은 `upsert_object_property_value` 미호출로 Neo4j에 없음.

**수정 완료:** ✅
- `graph_store.get_subgraph`: 노드 집합 수집 후 `MATCH (a)-[r]->(b) RETURN r, a.iri, b.iri` 방식으로 전체 엣지 조회 (collect(r) 드라이버 이슈 해결 포함)
- `graph_store.sync_object_property_values`: RELATION 전면 교체 메서드 추가
- `graph_store.batch_upsert_concepts`: SUBCLASS_OF 엣지 동기화 추가
- `sync_service.sync_tbox`: rdfs:subClassOf 쿼리 추가 + UUID→IRI 변환(_resolve_tbox) 수정
- `individuals.py` update: `sync_object_property_values` 호출 추가
- `ontologies.py`: `POST /{id}/sync` 엔드포인트 추가

---

## BUG-008 — Graph NodeDetailPanel Edit 버튼이 Entities 페이지로만 이동

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** 노드 클릭 → Edit 버튼 누르면 Entities 페이지로 이동만 할 뿐, 해당 엔티티의 편집 폼이 열리지 않음.

**기대 동작:** 해당 IRI의 엔티티를 즉시 편집할 수 있도록 편집 폼이 열려야 함.

**수정 대상:** GraphPage.tsx `onEdit` 콜백 — URL state나 query param으로 IRI 전달 후 EntitiesPage에서 수신 시 자동으로 편집 패널 열기.

---

## BUG-007 — 그래프 노드 클릭 시 Detail Panel 미표시

**발견:** Graph 탭 수동 테스트 (2026-03-31)

**현상:** 그래프에서 노드 클릭 시 우측 NodeDetailPanel이 나타나지 않음.

**원인:** `cyRef.current?.getElementById(id)` 가 빈 Cytoscape Collection을 반환할 때 `.data()` 호출 결과가 불안정.

**수정:** `GraphPage.tsx` — `selectedNodeEl.length > 0` 체크 후 `.data()` 호출하도록 변경. ✅ 수정 완료
