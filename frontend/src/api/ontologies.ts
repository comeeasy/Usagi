// Ontology CRUD API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Ontology, OntologyCreate, OntologyUpdate, PaginatedResponse } from '@/types/ontology'

// Backend returns {label, iri} but frontend types use {name, base_iri}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapOntology(data: any): Ontology {
  return { ...data, name: data.label ?? data.name, base_iri: data.iri ?? data.base_iri }
}

export function listOntologies(params?: { page?: number; pageSize?: number }): Promise<PaginatedResponse<Ontology>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies${query}`).then((res: PaginatedResponse<Ontology>) => ({
    ...res,
    items: res.items.map(mapOntology),
  }))
}

export function getOntology(id: string): Promise<Ontology> {
  return apiGet(`/ontologies/${id}`).then(mapOntology)
}

export function createOntology(data: OntologyCreate): Promise<Ontology> {
  return apiPost(`/ontologies`, {
    label: data.name,
    iri: data.base_iri,
    description: data.description,
    version: data.version,
  }).then(mapOntology)
}

export function updateOntology(id: string, data: OntologyUpdate): Promise<Ontology> {
  return apiPut(`/ontologies/${id}`, {
    label: data.name,
    description: data.description,
    version: data.version,
  }).then(mapOntology)
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

export function importOntologyFile(
  ontologyId: string,
  data: { format: string; content: string; file_name?: string },
): Promise<{ message: string; triples_imported?: number }> {
  return apiPost(`/ontologies/${ontologyId}/import/file`, data)
    .then((res: { imported: number }) => ({ message: `Imported ${res.imported} triples`, triples_imported: res.imported }))
}

export function importOntologyUrl(
  ontologyId: string,
  url: string,
): Promise<{ message: string; triples_imported?: number }> {
  return apiPost(`/ontologies/${ontologyId}/import/url`, { url })
    .then((res: { imported: number }) => ({ message: `Imported ${res.imported} triples`, triples_imported: res.imported }))
}

export function importOntologyStandard(
  ontologyId: string,
  name: string,
): Promise<{ message: string; triples_imported?: number }> {
  return apiPost(`/ontologies/${ontologyId}/import/standard`, { name })
    .then((res: { imported: number }) => ({ message: `Imported ${res.imported} triples`, triples_imported: res.imported }))
}

/** @deprecated Use importOntologyFile / importOntologyUrl / importOntologyStandard */
export function importOntology(
  ontologyId: string,
  data: { format: string; content?: string; url?: string; file_name?: string },
): Promise<{ message: string; triples_imported?: number }> {
  if (data.url) return importOntologyUrl(ontologyId, data.url)
  if (data.content) return importOntologyFile(ontologyId, { format: data.format, content: data.content, file_name: data.file_name })
  return Promise.reject(new Error('importOntology: url or content required'))
}

export function mergeOntologies(
  targetId: string,
  sourceId: string,
  strategy: string,
): Promise<{ message: string; merged_triples?: number }> {
  return apiPost(`/ontologies/${targetId}/merge`, { source_ontology_id: sourceId, strategy })
}
