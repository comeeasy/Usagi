// Ontology CRUD API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Ontology, OntologyCreate, OntologyUpdate, PaginatedResponse } from '@/types/ontology'

export function listOntologies(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<Ontology>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies${query}`)
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

export interface SubgraphData {
  nodes: Array<{ data: { id: string; label: string; type: string; iri: string } }>
  edges: Array<{ data: { id: string; source: string; target: string; label: string; type: string } }>
}

export function getSubgraph(
  ontologyId: string,
  params: { rootIris?: string[]; depth?: number; includeIndividuals?: boolean },
): Promise<SubgraphData> {
  return apiPost(`/ontologies/${ontologyId}/subgraph`, params)
}

export function importOntology(
  ontologyId: string,
  data: { format: string; content?: string; url?: string; file_name?: string },
): Promise<{ message: string; triples_imported?: number }> {
  return apiPost(`/ontologies/${ontologyId}/import`, data)
}

export function mergeOntologies(
  targetId: string,
  sourceId: string,
  strategy: string,
): Promise<{ message: string; merged_triples?: number }> {
  return apiPost(`/ontologies/${targetId}/merge`, { source_ontology_id: sourceId, strategy })
}
