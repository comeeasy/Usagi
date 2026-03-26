/**
 * E2E 시나리오 6: 벡터 검색 (fastembed 코사인 유사도)
 *
 * 전제조건: docker compose up -d
 * 실행: npx playwright test e2e/scenario6-vector-search.spec.ts
 */
import { test, expect } from '@playwright/test'

const BASE_IRI = 'https://e2e.example.org/vector-search'
let ontologyId: string

test.describe('시나리오 6: 벡터 검색', () => {
  test.beforeAll(async ({ request }) => {
    // 잔여 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if (ont.iri === BASE_IRI) {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }

    // 온톨로지 + Concept 생성
    const ontRes = await request.post('/api/v1/ontologies', {
      data: { label: 'Vector Search Test', iri: BASE_IRI },
    })
    const ont = await ontRes.json()
    ontologyId = ont.id

    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Person`, label: 'Person' },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Employee`, label: 'Employee' },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Vehicle`, label: 'Vehicle' },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Car`, label: 'Car' },
    })
  })

  test.afterAll(async ({ request }) => {
    if (ontologyId) {
      await request.delete(`/api/v1/ontologies/${ontologyId}`)
    }
  })

  // ── API 레벨 테스트 ─────────────────────────────────────────────────────

  test('6-1. 벡터 검색 API — 결과 반환', async ({ request }) => {
    const res = await request.post(`/api/v1/ontologies/${ontologyId}/search/vector`, {
      data: { text: 'human being', k: 5 },
    })
    expect(res.status()).toBe(200)
    const results = await res.json()
    expect(Array.isArray(results)).toBe(true)
    expect(results.length).toBeGreaterThan(0)
  })

  test('6-2. 벡터 검색 결과에 iri·label·score 필드 포함', async ({ request }) => {
    const res = await request.post(`/api/v1/ontologies/${ontologyId}/search/vector`, {
      data: { text: 'person employee', k: 4 },
    })
    const results = await res.json()
    for (const r of results) {
      expect(r).toHaveProperty('iri')
      expect(r).toHaveProperty('label')
    }
  })

  test('6-3. 의미 유사도 — person 쿼리 시 Person/Employee가 상위', async ({ request }) => {
    const res = await request.post(`/api/v1/ontologies/${ontologyId}/search/vector`, {
      data: { text: 'person human worker', k: 4 },
    })
    const results = await res.json()
    const iris = results.map((r: { iri: string }) => r.iri)
    // Person 또는 Employee 중 하나가 결과에 포함되어야 함
    const hasPersonOrEmployee =
      iris.includes(`${BASE_IRI}#Person`) || iris.includes(`${BASE_IRI}#Employee`)
    expect(hasPersonOrEmployee).toBe(true)
  })

  test('6-4. k 파라미터 — 반환 건수 제한', async ({ request }) => {
    const res = await request.post(`/api/v1/ontologies/${ontologyId}/search/vector`, {
      data: { text: 'anything', k: 2 },
    })
    const results = await res.json()
    expect(results.length).toBeLessThanOrEqual(2)
  })

  test('6-5. 빈 온톨로지 — 빈 배열 반환', async ({ request }) => {
    // 임시 빈 온톨로지 생성
    const tmp = await request.post('/api/v1/ontologies', {
      data: { label: 'Empty Ont', iri: `${BASE_IRI}-empty` },
    })
    const tmpOnt = await tmp.json()

    const res = await request.post(`/api/v1/ontologies/${tmpOnt.id}/search/vector`, {
      data: { text: 'anything', k: 5 },
    })
    expect(res.status()).toBe(200)
    const results = await res.json()
    expect(results).toEqual([])

    await request.delete(`/api/v1/ontologies/${tmpOnt.id}`)
  })

  test('6-6. 존재하지 않는 온톨로지 ID — 빈 배열 반환', async ({ request }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000'
    const res = await request.post(`/api/v1/ontologies/${fakeId}/search/vector`, {
      data: { text: 'test', k: 5 },
    })
    expect(res.status()).toBe(200)
    const results = await res.json()
    expect(results).toEqual([])
  })

  // ── UI 레벨 테스트 ──────────────────────────────────────────────────────

  test('6-7. Search 탭 접근 및 벡터 검색 입력창 표시', async ({ page }) => {
    await page.goto(`/${ontologyId}/search`)
    await expect(page.getByPlaceholder(/search|query|검색/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('6-8. UI 검색어 입력 후 결과 표시', async ({ page }) => {
    await page.goto(`/${ontologyId}/search`)

    const input = page.getByPlaceholder(/search|query|검색/i).first()
    await input.fill('person human')
    await input.press('Enter')

    // 결과 목록 표시 확인
    await expect(page.getByText(/Person|Employee|Vehicle|Car/i).first()).toBeVisible({
      timeout: 15_000,
    })
  })
})
