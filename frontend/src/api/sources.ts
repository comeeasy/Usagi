// Backing Source API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { BackingSource, BackingSourceCreate } from '@/types/source'
import type { PaginatedResponse, JobResponse } from '@/types/ontology'

export function listSources(
  ontologyId: string,
  params?: { page?: number; pageSize?: number },
): Promise<PaginatedResponse<BackingSource>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies/${ontologyId}/sources${query}`)
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
