// Backing Source API client stubs

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { BackingSource, BackingSourceCreate } from '@/types/source'
import type { PaginatedResponse } from '@/types/ontology'

// TODO: implement all functions

export function listSources(
  ontologyId: string,
  params?: { page?: number; pageSize?: number },
): Promise<PaginatedResponse<BackingSource>> {
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

export function triggerSync(ontologyId: string, sourceId: string): Promise<unknown> {
  // TODO: return apiPost(`/ontologies/${ontologyId}/sources/${sourceId}/sync`, {})
  throw new Error('Not implemented')
}
