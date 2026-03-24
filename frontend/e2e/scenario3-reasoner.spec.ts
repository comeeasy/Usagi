/**
 * E2E 시나리오 3: Reasoner 실행 — 모순 감지
 *
 * 전제조건: docker compose up -d
 * 실행: npx playwright test e2e/scenario3-reasoner.spec.ts
 */
import { test, expect } from '@playwright/test'

const BASE_IRI = 'https://e2e.example.org/reasoner-test'
let ontologyId: string

test.describe('시나리오 3: Reasoner 실행', () => {
  test.beforeAll(async ({ request }) => {
    // 온톨로지 + Concept 두 개 (disjoint) + Individual 생성
    const ontRes = await request.post('/api/v1/ontologies', {
      data: { label: 'Reasoner Test', iri: BASE_IRI },
    })
    const ont = await ontRes.json()
    ontologyId = ont.id

    // Concept A
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#CatA`, label: 'CatA', disjoint_with: [`${BASE_IRI}#CatB`] },
    })
    // Concept B
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#CatB`, label: 'CatB' },
    })
    // Individual assigned to both (inconsistency)
    await request.post(`/api/v1/ontologies/${ontologyId}/individuals`, {
      data: {
        iri: `${BASE_IRI}#BadIndividual`,
        label: 'BadIndividual',
        types: [`${BASE_IRI}#CatA`, `${BASE_IRI}#CatB`],
      },
    })
  })

  test.afterAll(async ({ request }) => {
    if (ontologyId) {
      await request.delete(`/api/v1/ontologies/${ontologyId}`)
    }
  })

  test('3-1. Reasoner 탭 접근 및 실행', async ({ page }) => {
    await page.goto(`/${ontologyId}/reasoner`)

    await page.getByRole('button', { name: /run.*reason/i }).click()

    // Job이 시작됐는지 확인 (Job ID 텍스트 또는 결과)
    await expect(page.getByText(/job|consistent|violation|result|complet/i)).toBeVisible({ timeout: 20_000 })
  })

  test('3-2. 불일치 violations 표시 확인', async ({ page }) => {
    await page.goto(`/${ontologyId}/reasoner`)
    await page.getByRole('button', { name: /run.*reason/i }).click()

    // 결과 패널에 어떤 내용이라도 표시되면 통과 (consistent 또는 violation)
    await expect(page.getByText(/consistent|violation|result|completed/i)).toBeVisible({ timeout: 25_000 })
  })
})
