/**
 * E2E 시나리오 1: 온톨로지 생성 → Entity 추가 → SPARQL 조회
 *
 * 전제조건: docker compose up -d (backend + frontend + Oxigraph)
 * 실행: npx playwright test e2e/scenario1-ontology-entity-sparql.spec.ts
 */
import { test, expect } from '@playwright/test'
import { deleteOntologyViaApi } from './helpers'

let ontologyId: string

test.describe('시나리오 1: 온톨로지 생성 → Entity 추가 → SPARQL 조회', () => {
  test.afterAll(async ({ request }) => {
    if (ontologyId) {
      await request.delete(`/api/v1/ontologies/${ontologyId}`)
    }
  })

  test('1-1. 홈에서 새 온톨로지 생성', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('New Ontology')).toBeVisible()

    await page.getByText('New Ontology').click()

    // 폼에 입력
    await page.getByPlaceholder('My Ontology').fill('E2E Test Ontology')
    await page.getByPlaceholder('https://example.org/my-ontology').fill('https://e2e.example.org/test')

    // 제출
    await page.getByRole('button', { name: /create/i }).click()

    // 생성된 카드가 홈에 표시
    await expect(page.getByText('E2E Test Ontology')).toBeVisible()
  })

  test('1-2. Entities 탭에서 Concept(Person) 추가', async ({ page }) => {
    // 온톨로지 카드 클릭하여 상세 이동
    await page.goto('/')
    await page.getByText('E2E Test Ontology').click()

    // entities 탭 클릭
    await page.getByRole('link', { name: /entities/i }).click()
    await expect(page.url()).toContain('/entities')

    // New Concept 클릭
    await page.getByRole('button', { name: /New Concept/i }).click()
    await expect(page.getByText(/Create Concept/i)).toBeVisible()

    // IRI 입력
    await page.getByPlaceholder(/https:\/\//i).fill('https://e2e.example.org/test#Person')
    await page.getByPlaceholder(/label/i).fill('Person')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByText('Person')).toBeVisible()
  })

  test('1-3. Individuals 탭에서 Individual(Alice) 추가', async ({ page }) => {
    await page.goto('/')
    await page.getByText('E2E Test Ontology').click()
    await page.getByRole('link', { name: /entities/i }).click()

    await page.getByText('individuals').click()
    await page.getByRole('button', { name: /New Individual/i }).click()

    await page.getByPlaceholder(/https:\/\//i).fill('https://e2e.example.org/test#Alice')
    await page.getByPlaceholder(/label/i).fill('Alice')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByText('Alice')).toBeVisible()
  })

  test('1-4. SPARQL 탭에서 Individual 조회', async ({ page }) => {
    await page.goto('/')
    await page.getByText('E2E Test Ontology').click()
    await page.getByRole('link', { name: /sparql/i }).click()

    // 기본 쿼리 지우고 새 쿼리 입력
    const editor = page.locator('.cm-content')
    await editor.click()
    await page.keyboard.press('Control+a')
    await page.keyboard.type('SELECT ?p WHERE { ?p a <http://www.w3.org/2002/07/owl#NamedIndividual> }')

    await page.getByRole('button', { name: /run/i }).click()

    // Alice 결과 확인
    await expect(page.getByText(/Alice/i)).toBeVisible({ timeout: 10_000 })
  })
})
