// Entity (Concept / Individual) API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Concept, ConceptCreate, ConceptUpdate } from '@/types/concept'
import type { Individual, IndividualCreate, IndividualUpdate } from '@/types/individual'
import type { PaginatedResponse } from '@/types/ontology'

export function listConcepts(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string },
): Promise<PaginatedResponse<Concept>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies/${ontologyId}/concepts${query}`)
}

export function getConcept(ontologyId: string, iri: string): Promise<Concept> {
  return apiGet(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}`)
}

export function createConcept(ontologyId: string, data: ConceptCreate): Promise<Concept> {
  return apiPost(`/ontologies/${ontologyId}/concepts`, data)
}

export function updateConcept(ontologyId: string, iri: string, data: ConceptUpdate): Promise<Concept> {
  return apiPut(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}`, data)
}

export function deleteConcept(ontologyId: string, iri: string): Promise<void> {
  return apiDelete(`/ontologies/${ontologyId}/concepts/${encodeURIComponent(iri)}`)
}

export function listIndividuals(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string },
): Promise<PaginatedResponse<Individual>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies/${ontologyId}/individuals${query}`)
}

export function getIndividual(ontologyId: string, iri: string): Promise<Individual> {
  return apiGet(`/ontologies/${ontologyId}/individuals/${encodeURIComponent(iri)}`)
}

export function createIndividual(ontologyId: string, data: IndividualCreate): Promise<Individual> {
  return apiPost(`/ontologies/${ontologyId}/individuals`, data)
}

export function updateIndividual(ontologyId: string, iri: string, data: IndividualUpdate): Promise<Individual> {
  return apiPut(`/ontologies/${ontologyId}/individuals/${encodeURIComponent(iri)}`, data)
}

export function deleteIndividual(ontologyId: string, iri: string): Promise<void> {
  return apiDelete(`/ontologies/${ontologyId}/individuals/${encodeURIComponent(iri)}`)
}

export function searchEntities(
  ontologyId: string,
  q: string,
  kind?: string,
  limit = 20,
): Promise<Array<Concept | Individual>> {
  const qs = new URLSearchParams({ q, limit: String(limit) })
  if (kind && kind !== 'all') qs.set('kind', kind)
  return apiGet(`/ontologies/${ontologyId}/search/entities?${qs.toString()}`)
}

export function vectorSearch(ontologyId: string, text: string, k = 10): Promise<Array<Concept | Individual>> {
  return apiPost(`/ontologies/${ontologyId}/search/vector`, { text, k })
}
