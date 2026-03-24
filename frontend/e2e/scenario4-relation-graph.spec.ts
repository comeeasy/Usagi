/**
 * E2E 시나리오 4: Relation 생성 → 그래프 뷰 확인
 *
 * 전제조건: docker compose up -d
 * 실행: npx playwright test e2e/scenario4-relation-graph.spec.ts
 */
import { test, expect } from '@playwright/test'

const BASE_IRI = 'https://e2e.example.org/relation-test'
let ontologyId: string

test.describe('시나리오 4: Relation 생성 → 그래프 뷰', () => {
  test.beforeAll(async ({ request }) => {
    const ontRes = await request.post('/api/v1/ontologies', {
      data: { label: 'Relation Test', iri: BASE_IRI },
    })
    const ont = await ontRes.json()
    ontologyId = ont.id

    // Concepts
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Employee`, label: 'Employee' },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Department`, label: 'Department' },
    })
  })

  test.afterAll(async ({ request }) => {
    if (ontologyId) {
      await request.delete(`/api/v1/ontologies/${ontologyId}`)
    }
  })

  test('4-1. Relations 탭에서 Object Property 생성', async ({ page }) => {
    await page.goto(`/${ontologyId}/relations`)

    await page.getByRole('button', { name: /New Property/i }).click()
    await expect(page.getByText(/Create Property/i)).toBeVisible()

    await page.getByPlaceholder(/https:\/\//i).fill(`${BASE_IRI}#worksFor`)
    await page.getByPlaceholder(/label/i).fill('worksFor')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByRole('cell', { name: 'worksFor', exact: true })).toBeVisible({ timeout: 5_000 })
  })

  test('4-2. Graph 탭에서 노드 렌더링 확인', async ({ page }) => {
    await page.goto(`/${ontologyId}/graph`)

    // Load Graph 버튼 클릭 → 캔버스 렌더링 확인
    await page.getByRole('button', { name: /Load Graph/i }).click()
    const graphCanvas = page.locator('canvas, svg').first()
    await expect(graphCanvas).toBeVisible({ timeout: 15_000 })
  })
})
