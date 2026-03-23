// Ontology CRUD API client stubs

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Ontology, OntologyCreate, OntologyUpdate, PaginatedResponse } from '@/types/ontology'

// TODO: implement all functions

export function listOntologies(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<Ontology>> {
  // TODO: const qs = new URLSearchParams({ page: ..., page_size: ... })
  return apiGet(`/ontologies`)
}

export function getOntology(id: string): Promise<Ontology> {
  return apiGet(`/ontologies/${id}`)
}

export function createOntology(data: OntologyCreate): Promise<Ontology> {
  return apiPost(`/ontologies`, data)
}

export function updateOntology(id: string, data: OntologyUpdate): Promise<Ontology> {
  return apiPut(`/ontologies/${id}`, data)
}

export function deleteOntology(id: string): Promise<void> {
  return apiDelete(`/ontologies/${id}`)
}

export function getSubgraph(
  ontologyId: string,
  params: { rootIris?: string[]; depth?: number; includeIndividuals?: boolean },
): Promise<unknown> {
  // TODO: return apiPost(`/ontologies/${ontologyId}/subgraph`, params)
  throw new Error('Not implemented')
}
