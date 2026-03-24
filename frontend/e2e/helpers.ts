import { type Page } from '@playwright/test'

export const API_BASE = process.env.E2E_API_BASE ?? 'http://localhost/api/v1'

/** 테스트용 온톨로지 직접 생성 (UI 우회) */
export async function createOntologyViaApi(page: Page, label: string, baseIri: string) {
  const res = await page.request.post(`${API_BASE}/ontologies`, {
    data: { label, iri: baseIri, description: `E2E test ontology: ${label}` },
  })
  return res.json() as Promise<{ id: string; iri: string }>
}

/** 테스트용 온톨로지 삭제 (cleanup) */
export async function deleteOntologyViaApi(page: Page, ontologyId: string) {
  await page.request.delete(`${API_BASE}/ontologies/${ontologyId}`)
}
