/**
 * 튜토리얼용 스크린샷 캡처 스크립트
 * 실행: npx playwright test e2e/capture-screenshots.ts --reporter=line
 */
import { test, expect } from '@playwright/test'

const OUT = '/Users/joono/projects/docs/screenshots'
const BASE_IRI = 'https://tutorial.example.org/company'
let ontologyId: string

test.describe('스크린샷 캡처', () => {
  test.beforeAll(async ({ request }) => {
    // 기존 튜토리얼 온톨로지 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if (ont.iri === BASE_IRI || ont.label === 'Company Ontology') {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }
    // 튜토리얼용 온톨로지 생성
    const cr = await request.post('/api/v1/ontologies', {
      data: { label: 'Company Ontology', iri: BASE_IRI, description: '회사 도메인 온톨로지 예제' },
    })
    const created = await cr.json()
    ontologyId = created.id

    // 컨셉 생성
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Person`, label: 'Person', comment: '사람을 나타내는 클래스' },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Employee`, label: 'Employee', comment: '직원 클래스', parent_iris: [`${BASE_IRI}#Person`] },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/concepts`, {
      data: { iri: `${BASE_IRI}#Department`, label: 'Department', comment: '부서 클래스' },
    })

    // 프로퍼티 생성
    await request.post(`/api/v1/ontologies/${ontologyId}/properties`, {
      data: { iri: `${BASE_IRI}#worksIn`, label: 'worksIn', kind: 'object', domain_iri: `${BASE_IRI}#Employee`, range_iri: `${BASE_IRI}#Department` },
    })

    // Individual 생성
    await request.post(`/api/v1/ontologies/${ontologyId}/individuals`, {
      data: { iri: `${BASE_IRI}#alice`, label: 'Alice', type_iris: [`${BASE_IRI}#Employee`] },
    })
    await request.post(`/api/v1/ontologies/${ontologyId}/individuals`, {
      data: { iri: `${BASE_IRI}#engineering`, label: 'Engineering', type_iris: [`${BASE_IRI}#Department`] },
    })
  })

  test.afterAll(async ({ request }) => {
    if (ontologyId) await request.delete(`/api/v1/ontologies/${ontologyId}`)
  })

  test('01 홈페이지', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Company Ontology')).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: `${OUT}/01-homepage.png`, fullPage: false })
  })

  test('02 온톨로지 생성 모달', async ({ page }) => {
    await page.goto('/')
    await page.getByText('New Ontology').click()
    await expect(page.getByText('Base IRI')).toBeVisible()
    await page.getByPlaceholder('My Ontology').fill('My New Ontology')
    await page.getByPlaceholder('https://example.org/myontology/').fill('https://example.org/my-new/')
    await page.screenshot({ path: `${OUT}/02-create-ontology-modal.png`, fullPage: false })
  })

  test('03 Entities 페이지 — Concepts', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)
    await expect(page.getByRole('cell', { name: 'Person', exact: true })).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: `${OUT}/03-entities-concepts.png`, fullPage: false })
  })

  test('04 Concept 생성 폼', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)
    await page.getByRole('button', { name: /New Concept/i }).click()
    await expect(page.getByText(/Create Concept/i)).toBeVisible()
    await page.getByPlaceholder(/https:\/\//i).first().fill(`${BASE_IRI}#Manager`)
    await page.getByPlaceholder(/label/i).fill('Manager')
    await page.screenshot({ path: `${OUT}/04-concept-create-form.png`, fullPage: false })
  })

  test('05 Entities 페이지 — Individuals', async ({ page }) => {
    await page.goto(`/${ontologyId}/entities`)
    await page.getByRole('button', { name: 'individuals', exact: true }).click()
    await expect(page.getByRole('cell', { name: 'Alice', exact: true })).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: `${OUT}/05-entities-individuals.png`, fullPage: false })
  })

  test('06 Relations 페이지', async ({ page }) => {
    await page.goto(`/${ontologyId}/relations`)
    await expect(page.getByRole('cell', { name: 'worksIn', exact: true })).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: `${OUT}/06-relations.png`, fullPage: false })
  })

  test('07 SPARQL 페이지', async ({ page }) => {
    await page.goto(`/${ontologyId}/sparql`)
    await expect(page.locator('.cm-content')).toBeVisible({ timeout: 10_000 })
    // 기본 쿼리 실행
    await page.getByRole('button', { name: /run/i }).click()
    await page.waitForTimeout(2000)
    await page.screenshot({ path: `${OUT}/07-sparql.png`, fullPage: false })
  })

  test('08 Import 페이지', async ({ page }) => {
    await page.goto(`/${ontologyId}/import`)
    await expect(page.getByText('Import Ontology')).toBeVisible()
    await page.screenshot({ path: `${OUT}/08-import-file.png`, fullPage: false })

    // Standard Ontologies 탭
    await page.getByRole('button', { name: /Standard Ontologies/i }).click()
    await page.screenshot({ path: `${OUT}/08b-import-standard.png`, fullPage: false })
  })

  test('09 Graph 페이지', async ({ page }) => {
    await page.goto(`/${ontologyId}/graph`)
    await expect(page.getByRole('button', { name: /Load Graph/i })).toBeVisible()
    await page.getByRole('button', { name: /Load Graph/i }).click()
    await page.waitForTimeout(2000)
    await page.screenshot({ path: `${OUT}/09-graph.png`, fullPage: false })
  })

  test('10 Reasoner 페이지', async ({ page }) => {
    await page.goto(`/${ontologyId}/reasoner`)
    await expect(page.getByRole('button', { name: /run.*reason/i })).toBeVisible({ timeout: 10_000 })
    await page.screenshot({ path: `${OUT}/10-reasoner.png`, fullPage: false })
  })
})
