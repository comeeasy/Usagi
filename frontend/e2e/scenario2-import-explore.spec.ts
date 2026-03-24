/**
 * E2E 시나리오 2: 온톨로지 Import → 탐색
 *
 * 전제조건: docker compose up -d
 * 실행: npx playwright test e2e/scenario2-import-explore.spec.ts
 */
import { test, expect } from '@playwright/test'

let ontologyId: string

test.describe('시나리오 2: 온톨로지 Import → 탐색', () => {
  test.beforeAll(async ({ request }) => {
    // 테스트용 온톨로지 미리 생성
    const res = await request.post('/api/v1/ontologies', {
      data: {
        label: 'Import Test Ontology',
        iri: 'https://e2e.example.org/import-test',
        description: 'E2E import test',
      },
    })
    const data = await res.json()
    ontologyId = data.id
  })

  test.afterAll(async ({ request }) => {
    if (ontologyId) {
      await request.delete(`/api/v1/ontologies/${ontologyId}`)
    }
  })

  test('2-1. Import 탭에서 FOAF 표준 온톨로지 Import', async ({ page }) => {
    await page.goto(`/${ontologyId}/import`)

    // "Standard Ontologies" 탭 클릭 후 FOAF 라디오 선택 → Import Selected
    await page.getByRole('button', { name: /Standard Ontologies/i }).click()
    await page.getByText('FOAF', { exact: true }).click()
    await page.getByRole('button', { name: /Import Selected/i }).click()
    await expect(page.getByText(/import(ed|ing|success|complet)/i)).toBeVisible({ timeout: 20_000 })
  })

  test('2-2. Entities 탭에서 foaf:Person 확인', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)

    // 로딩 완료 대기
    await expect(page.getByText(/Person/i)).toBeVisible({ timeout: 10_000 })
  })

  test('2-3. 검색으로 필터링', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)

    await page.getByPlaceholder(/search/i).fill('Person')

    // 검색 결과 - Person 포함
    await expect(page.getByText('Person')).toBeVisible({ timeout: 5_000 })
  })
})
