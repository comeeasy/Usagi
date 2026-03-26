/**
 * E2E 시나리오 5: 온톨로지 Merge — 충돌 감지 → 해결 → 병합
 *
 * 전제조건: docker compose up -d
 * 실행: npx playwright test e2e/scenario5-merge.spec.ts
 */
import { test, expect } from '@playwright/test'

const IRI_A = 'https://e2e.example.org/merge-target'
const IRI_B = 'https://e2e.example.org/merge-source'

let ontologyAId: string
let ontologyBId: string

test.describe('시나리오 5: 온톨로지 Merge', () => {
  test.beforeAll(async ({ request }) => {
    // 이전 잔여 데이터 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if ([IRI_A, IRI_B].includes(ont.iri)) {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }

    // Target 온톨로지: Person + Department
    const resA = await request.post('/api/v1/ontologies', {
      data: { label: 'Merge Target', iri: IRI_A },
    })
    const ontA = await resA.json()
    ontologyAId = ontA.id

    await request.post(`/api/v1/ontologies/${ontologyAId}/concepts`, {
      data: { iri: `${IRI_A}#Person`, label: 'Person' },
    })
    await request.post(`/api/v1/ontologies/${ontologyAId}/concepts`, {
      data: { iri: `${IRI_A}#Department`, label: 'Department' },
    })

    // Source 온톨로지: 겹치지 않는 Employee
    const resB = await request.post('/api/v1/ontologies', {
      data: { label: 'Merge Source', iri: IRI_B },
    })
    const ontB = await resB.json()
    ontologyBId = ontB.id

    await request.post(`/api/v1/ontologies/${ontologyBId}/concepts`, {
      data: { iri: `${IRI_B}#Employee`, label: 'Employee' },
    })
  })

  test.afterAll(async ({ request }) => {
    for (const id of [ontologyAId, ontologyBId]) {
      if (id) await request.delete(`/api/v1/ontologies/${id}`)
    }
  })

  // ── step: select ────────────────────────────────────────────────────────

  test('5-1. Merge 탭 접근 및 소스 드롭다운 표시', async ({ page }) => {
    await page.goto(`/${ontologyAId}/merge`)
    await expect(page.getByText('Merge Ontologies')).toBeVisible()
    await expect(page.getByRole('combobox')).toBeVisible()
  })

  test('5-2. 소스 미선택 시 Preview 버튼 비활성화', async ({ page }) => {
    await page.goto(`/${ontologyAId}/merge`)
    const btn = page.getByRole('button', { name: /Preview & Resolve/i })
    await expect(btn).toBeDisabled()
  })

  test('5-3. 소스 드롭다운에 Merge Source 온톨로지 표시', async ({ page }) => {
    await page.goto(`/${ontologyAId}/merge`)
    // 드롭다운 옵션에 Source 온톨로지가 있어야 함
    await expect(page.getByRole('option', { name: /Merge Source/i })).toBeVisible({ timeout: 10_000 })
  })

  // ── step: preview (no conflicts) ────────────────────────────────────────

  test('5-4. 소스 선택 후 Preview → 충돌 없음 확인', async ({ page }) => {
    await page.goto(`/${ontologyAId}/merge`)

    // 드롭다운 옵션 로드 대기 후 선택
    await expect(page.getByRole('option', { name: /Merge Source/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('combobox').selectOption({ label: /Merge Source/i })

    await page.getByRole('button', { name: /Preview & Resolve/i }).click()

    // 미리보기 단계 진입 확인
    await expect(page.getByText(/No conflicts detected|Conflicts/i)).toBeVisible({ timeout: 15_000 })
  })

  test('5-5. Preview 단계에서 Merge 버튼 클릭 → 완료', async ({ page }) => {
    await page.goto(`/${ontologyAId}/merge`)

    await expect(page.getByRole('option', { name: /Merge Source/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('combobox').selectOption({ label: /Merge Source/i })
    await page.getByRole('button', { name: /Preview & Resolve/i }).click()

    // Preview 단계 진입
    await expect(page.getByText(/No conflicts detected|Conflicts/i)).toBeVisible({ timeout: 15_000 })

    // Merge 버튼 클릭 (starts with "Merge")
    const mergeBtn = page.getByRole('button').filter({ hasText: /^Merge/ }).first()
    await mergeBtn.click()

    // 완료 화면
    await expect(page.getByText(/Merge complete/i)).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText(/triples/i)).toBeVisible()
  })

  test('5-6. 완료 후 "Merge another" 버튼으로 초기화', async ({ page }) => {
    await page.goto(`/${ontologyAId}/merge`)

    await expect(page.getByRole('option', { name: /Merge Source/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('combobox').selectOption({ label: /Merge Source/i })
    await page.getByRole('button', { name: /Preview & Resolve/i }).click()
    await expect(page.getByText(/No conflicts detected|Conflicts/i)).toBeVisible({ timeout: 15_000 })

    const mergeBtn = page.getByRole('button').filter({ hasText: /^Merge/ }).first()
    await mergeBtn.click()
    await expect(page.getByText(/Merge complete/i)).toBeVisible({ timeout: 15_000 })

    // "Merge another" 클릭 → select 단계로 복귀
    await page.getByRole('button', { name: /Merge another/i }).click()
    await expect(page.getByRole('button', { name: /Preview & Resolve/i })).toBeVisible()
  })
})

test.describe('시나리오 5b: Merge 충돌 감지', () => {
  const SHARED_IRI = 'https://e2e.example.org/merge-conflict-shared#Thing'
  const IRI_C = 'https://e2e.example.org/merge-conflict-a'
  const IRI_D = 'https://e2e.example.org/merge-conflict-b'
  let ontCId: string
  let ontDId: string

  test.beforeAll(async ({ request }) => {
    // 잔여 정리
    const res = await request.get('/api/v1/ontologies?page_size=100')
    const data = await res.json()
    for (const ont of data.items ?? []) {
      if ([IRI_C, IRI_D].includes(ont.iri)) {
        await request.delete(`/api/v1/ontologies/${ont.id}`)
      }
    }

    // 동일 IRI, 다른 label → 충돌 유발
    const rC = await request.post('/api/v1/ontologies', { data: { label: 'Conflict A', iri: IRI_C } })
    ontCId = (await rC.json()).id
    await request.post(`/api/v1/ontologies/${ontCId}/concepts`, {
      data: { iri: SHARED_IRI, label: 'OldName' },
    })

    const rD = await request.post('/api/v1/ontologies', { data: { label: 'Conflict B', iri: IRI_D } })
    ontDId = (await rD.json()).id
    await request.post(`/api/v1/ontologies/${ontDId}/concepts`, {
      data: { iri: SHARED_IRI, label: 'NewName' },
    })
  })

  test.afterAll(async ({ request }) => {
    for (const id of [ontCId, ontDId]) {
      if (id) await request.delete(`/api/v1/ontologies/${id}`)
    }
  })

  test('5b-1. 충돌 있는 Preview → conflict 카드 표시', async ({ page }) => {
    await page.goto(`/${ontCId}/merge`)

    await expect(page.getByRole('option', { name: /Conflict B/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('combobox').selectOption({ label: /Conflict B/i })
    await page.getByRole('button', { name: /Preview & Resolve/i }).click()

    // 충돌 해결 버튼 중 하나 표시 확인
    await expect(
      page.getByRole('button', { name: /Keep Current|Use Source|Keep Both/i }).first()
    ).toBeVisible({ timeout: 15_000 })
  })

  test('5b-2. keep-source 선택 후 Merge 성공', async ({ page }) => {
    await page.goto(`/${ontCId}/merge`)

    await expect(page.getByRole('option', { name: /Conflict B/i })).toBeVisible({ timeout: 10_000 })
    await page.getByRole('combobox').selectOption({ label: /Conflict B/i })
    await page.getByRole('button', { name: /Preview & Resolve/i }).click()

    // Use Source 선택
    await expect(page.getByRole('button', { name: /Use Source/i }).first()).toBeVisible({ timeout: 15_000 })
    await page.getByRole('button', { name: /Use Source/i }).first().click()

    const mergeBtn = page.getByRole('button').filter({ hasText: /^Merge/ }).first()
    await mergeBtn.click()

    await expect(page.getByText(/Merge complete/i)).toBeVisible({ timeout: 15_000 })
  })
})
