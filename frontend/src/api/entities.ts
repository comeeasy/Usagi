// Entity (Concept / Individual) API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Concept, ConceptCreate, ConceptUpdate } from '@/types/concept'
import type { Individual, IndividualCreate, IndividualUpdate } from '@/types/individual'
import type { PaginatedResponse } from '@/types/ontology'

export function listConcepts(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string; dataset?: string; root?: boolean },
): Promise<PaginatedResponse<Concept>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  if (params?.dataset) qs.set('dataset', params.dataset)
  if (params?.root) qs.set('root', 'true')
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies/${ontologyId}/concepts${query}`)
}

export function listSubclasses(
  ontologyId: string,
  iri: string,
  params?: { page?: number; pageSize?: number; dataset?: string },
): Promise<PaginatedResponse<Concept>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.dataset) qs.set('dataset', params.dataset)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}/subclasses${query}`)
}

export function getConcept(ontologyId: string, iri: string, dataset?: string): Promise<Concept> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiGet(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}${qs}`)
}

export function createConcept(ontologyId: string, data: ConceptCreate, dataset?: string): Promise<Concept> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/concepts${qs}`, data)
}

export function updateConcept(ontologyId: string, iri: string, data: ConceptUpdate, dataset?: string): Promise<Concept> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPut(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}${qs}`, data)
}

export function deleteConcept(ontologyId: string, iri: string, dataset?: string): Promise<void> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiDelete(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}${qs}`)
}

export function listIndividuals(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string; dataset?: string },
): Promise<PaginatedResponse<Individual>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  if (params?.dataset) qs.set('dataset', params.dataset)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies/${ontologyId}/individuals${query}`)
}

export function getIndividual(ontologyId: string, iri: string, dataset?: string): Promise<Individual> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiGet(`/ontologies/${ontologyId}/individuals/${encodeURIComponent(iri)}${qs}`)
}

export function createIndividual(ontologyId: string, data: IndividualCreate, dataset?: string): Promise<Individual> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/individuals${qs}`, data)
}

export function updateIndividual(ontologyId: string, iri: string, data: IndividualUpdate, dataset?: string): Promise<Individual> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPut(`/ontologies/${ontologyId}/individuals/${encodeURIComponent(iri)}${qs}`, data)
}

export function deleteIndividual(ontologyId: string, iri: string, dataset?: string): Promise<void> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiDelete(`/ontologies/${ontologyId}/individuals/${encodeURIComponent(iri)}${qs}`)
}

export function searchEntities(
  ontologyId: string,
  q: string,
  kind?: string,
  limit = 20,
  dataset?: string,
): Promise<Array<Concept | Individual>> {
  const qs = new URLSearchParams({ q, limit: String(limit) })
  if (kind && kind !== 'all') qs.set('kind', kind)
  if (dataset) qs.set('dataset', dataset)
  return apiGet(`/ontologies/${ontologyId}/search/entities?${qs.toString()}`)
}

export function vectorSearch(ontologyId: string, text: string, k = 10, dataset?: string): Promise<Array<Concept | Individual>> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/search/vector${qs}`, { text, k })
}
