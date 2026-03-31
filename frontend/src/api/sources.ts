// Backing Source API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { BackingSource, BackingSourceCreate, UploadResult } from '@/types/source'
import type { JobResponse } from '@/types/ontology'

export function listSources(ontologyId: string): Promise<BackingSource[]> {
  return apiGet(`/ontologies/${ontologyId}/sources`)
}

export function getSource(ontologyId: string, sourceId: string): Promise<BackingSource> {
  return apiGet(`/ontologies/${ontologyId}/sources/${sourceId}`)
}

export function createSource(ontologyId: string, data: BackingSourceCreate): Promise<BackingSource> {
  return apiPost(`/ontologies/${ontologyId}/sources`, data)
}

export function updateSource(
  ontologyId: string,
  sourceId: string,
  data: Partial<BackingSourceCreate>,
): Promise<BackingSource> {
  return apiPut(`/ontologies/${ontologyId}/sources/${sourceId}`, data)
}

export function deleteSource(ontologyId: string, sourceId: string): Promise<void> {
  return apiDelete(`/ontologies/${ontologyId}/sources/${sourceId}`)
}

export function triggerSync(ontologyId: string, sourceId: string): Promise<JobResponse> {
  return apiPost(`/ontologies/${ontologyId}/sources/${sourceId}/sync`, {})
}

export async function uploadCsvFile(
  ontologyId: string,
  sourceId: string,
  file: File,
): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  // apiPost는 JSON만 지원하므로 fetch 직접 사용
  const base = (await import('./client')).API_BASE_URL
  const res = await fetch(`${base}/ontologies/${ontologyId}/sources/${sourceId}/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }))
    throw new Error(err.detail ?? err.message ?? 'Upload failed')
  }
  return res.json()
}
