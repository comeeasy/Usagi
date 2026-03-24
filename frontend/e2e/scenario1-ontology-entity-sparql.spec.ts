/**
 * E2E 시나리오 1: 온톨로지 생성 → Entity 추가 → SPARQL 조회
 *
 * 전제조건: docker compose up -d (backend + frontend + Oxigraph)
 * 실행: npx playwright test e2e/scenario1-ontology-entity-sparql.spec.ts
 */
import { test, expect } from '@playwright/test'

const TEST_LABEL = 'E2E Test Ontology'
const TEST_IRI = 'https://e2e.example.org/test'

test.describe('시나리오 1: 온톨로지 생성 → Entity 추가 → SPARQL 조회', () => {
  test.beforeAll(async ({ request }) => {
    // 이전 실행 잔여 데이터 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if (ont.iri === TEST_IRI || ont.label === TEST_LABEL) {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }
  })

  test.afterAll(async ({ request }) => {
    // 테스트 종료 후 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if (ont.iri === TEST_IRI || ont.label === TEST_LABEL) {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }
  })

  test('1-1. 홈에서 새 온톨로지 생성', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('New Ontology')).toBeVisible()

    await page.getByText('New Ontology').click()

    // 폼에 입력
    await page.getByPlaceholder('My Ontology').fill(TEST_LABEL)
    await page.getByPlaceholder('https://example.org/myontology/').fill(TEST_IRI)

    // 제출
    await page.getByRole('button', { name: /create/i }).click()

    // 생성된 카드가 홈에 표시
    await expect(page.getByText(TEST_LABEL)).toBeVisible({ timeout: 10_000 })
  })

  test('1-2. Entities 탭에서 Concept(Person) 추가', async ({ page }) => {
    await page.goto('/')
    await page.getByText(TEST_LABEL).click()

    // entities 탭 클릭
    await page.getByRole('link', { name: /entities/i }).click()
    await expect(page.url()).toContain('/entities')

    // New Concept 클릭
    await page.getByRole('button', { name: /New Concept/i }).click()
    await expect(page.getByText(/Create Concept/i)).toBeVisible()

    // IRI 입력
    await page.getByPlaceholder(/https:\/\//i).fill(`${TEST_IRI}#Person`)
    await page.getByPlaceholder(/label/i).fill('Person')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByRole('cell', { name: 'Person', exact: true })).toBeVisible({ timeout: 5_000 })
  })

  test('1-3. Individuals 탭에서 Individual(Alice) 추가', async ({ page }) => {
    await page.goto('/')
    await page.getByText(TEST_LABEL).click()
    await page.getByRole('link', { name: /entities/i }).click()

    await page.getByText('individuals').click()
    await page.getByRole('button', { name: /New Individual/i }).click()

    await page.getByPlaceholder(/https:\/\//i).fill(`${TEST_IRI}#Alice`)
    await page.getByPlaceholder(/label/i).fill('Alice')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByRole('cell', { name: 'Alice', exact: true })).toBeVisible({ timeout: 5_000 })
  })

  test('1-4. SPARQL 탭에서 Individual 조회', async ({ page }) => {
    await page.goto('/')
    await page.getByText(TEST_LABEL).click()
    await page.getByRole('link', { name: /sparql/i }).click()

    // 기본 쿼리 지우고 새 쿼리 입력
    const editor = page.locator('.cm-content')
    await editor.click()
    await page.keyboard.press('Control+a')
    await page.keyboard.type('SELECT ?p WHERE { GRAPH ?g { ?p a <http://www.w3.org/2002/07/owl#NamedIndividual> } }')

    await page.getByRole('button', { name: /run/i }).click()

    // Alice IRI 결과 확인
    await expect(page.getByText(/Alice/i)).toBeVisible({ timeout: 10_000 })
  })
})
