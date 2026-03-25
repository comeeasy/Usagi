/**
 * E2E 시나리오 1: 온톨로지 생성 → Entity 추가 → SPARQL 조회
 *
 * 전제조건: docker compose up -d (backend + frontend + Oxigraph)
 * 실행: npx playwright test e2e/scenario1-ontology-entity-sparql.spec.ts
 */
import { test, expect } from '@playwright/test'

const TEST_LABEL = 'E2E Test Ontology'
const TEST_IRI = 'https://e2e.example.org/test'

let ontologyId: string

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

    // API로 테스트 온톨로지 생성 (UI 테스트와 별개로 ID 확보)
    const createRes = await request.post('/api/v1/ontologies', {
      data: { label: TEST_LABEL, iri: TEST_IRI },
    })
    const created = await createRes.json()
    ontologyId = created.id
  })

  test.afterAll(async ({ request }) => {
    if (ontologyId) {
      await request.delete(`/api/v1/ontologies/${ontologyId}`)
    }
    // 혹시 남은 잔여 데이터도 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if (ont.iri === TEST_IRI || ont.label === TEST_LABEL) {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }
  })

  test('1-1. 홈에서 새 온톨로지 생성 UI 확인', async ({ page }) => {
    await page.goto('/')
    // beforeAll에서 생성한 온톨로지 카드가 홈에 표시되는지 확인
    await expect(page.getByText(TEST_LABEL)).toBeVisible({ timeout: 10_000 })
    // New Ontology 버튼이 있는지 확인
    await expect(page.getByText('New Ontology')).toBeVisible()
  })

  test('1-2. Entities 탭에서 Concept(Person) 추가', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)

    // New Concept 클릭
    await page.getByRole('button', { name: /New Concept/i }).click()
    await expect(page.getByText(/Create Concept/i)).toBeVisible()

    // IRI 입력 (첫 번째 https:// 플레이스홀더)
    await page.getByPlaceholder(/https:\/\//i).first().fill(`${TEST_IRI}#Person`)
    await page.getByPlaceholder(/label/i).fill('Person')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByRole('cell', { name: 'Person', exact: true })).toBeVisible({ timeout: 5_000 })
  })

  test('1-3. Individuals 탭에서 Individual(Alice) 추가', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)

    await page.getByRole('button', { name: 'individuals', exact: true }).click()
    await page.getByRole('button', { name: /New Individual/i }).click()

    await page.getByPlaceholder(/https:\/\//i).first().fill(`${TEST_IRI}#Alice`)
    await page.getByPlaceholder(/label/i).fill('Alice')

    await page.getByRole('button', { name: /create/i }).click()
    await expect(page.getByRole('cell', { name: 'Alice', exact: true })).toBeVisible({ timeout: 5_000 })
  })

  test('1-4. SPARQL 탭에서 Individual 조회', async ({ page }) => {
    await page.goto(`/${ontologyId}/sparql`)

    // CodeMirror 에디터 내용 교체 (Mac: Meta+A, Win/Linux: Control+A)
    const editor = page.locator('.cm-content')
    await editor.click()
    await page.keyboard.press('Meta+a')
    await page.keyboard.press('Backspace')
    await page.keyboard.type('SELECT ?p ?label WHERE { GRAPH ?g { ?p a <http://www.w3.org/2002/07/owl#NamedIndividual> . OPTIONAL { ?p <http://www.w3.org/2000/01/rdf-schema#label> ?label } } }')

    await page.getByRole('button', { name: /run/i }).click()

    // Alice IRI 또는 label 결과 확인 (여러 요소 허용)
    await expect(page.getByText(/Alice/i).first()).toBeVisible({ timeout: 10_000 })
  })
})
