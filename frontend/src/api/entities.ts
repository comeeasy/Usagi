// Entity (Concept / Individual) API client stubs

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Concept, ConceptCreate, ConceptUpdate } from '@/types/concept'
import type { Individual, IndividualCreate } from '@/types/individual'
import type { PaginatedResponse } from '@/types/ontology'

// TODO: implement all functions

export function listConcepts(
  ontologyId: string,
  params?: { page?: number; pageSize?: number },
): Promise<PaginatedResponse<Concept>> {
  return apiGet(`/ontologies/${ontologyId}/concepts`)
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
  params?: { page?: number; pageSize?: number },
): Promise<PaginatedResponse<Individual>> {
  return apiGet(`/ontologies/${ontologyId}/individuals`)
}

export function createIndividual(ontologyId: string, data: IndividualCreate): Promise<Individual> {
  return apiPost(`/ontologies/${ontologyId}/individuals`, data)
}

export function searchEntities(
  ontologyId: string,
  q: string,
  kind?: string,
  limit = 20,
): Promise<unknown[]> {
  // TODO: return apiGet(`/ontologies/${ontologyId}/search/entities?q=${q}&kind=${kind}&limit=${limit}`)
  throw new Error('Not implemented')
}

export function vectorSearch(ontologyId: string, text: string, k = 10): Promise<unknown[]> {
  // TODO: return apiPost(`/ontologies/${ontologyId}/search/vector`, { text, k })
  throw new Error('Not implemented')
}
