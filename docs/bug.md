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

**수정 대상:** Concept 생성/편집 폼 컴포넌트
