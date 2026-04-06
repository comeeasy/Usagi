// Relations (ObjectProperty / DataProperty) API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { ObjectProperty, DataProperty, ObjectPropertyCreate, DataPropertyCreate } from '@/types/property'
import type { PaginatedResponse } from '@/types/ontology'

export function listObjectProperties(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string; dataset?: string },
): Promise<PaginatedResponse<ObjectProperty>> {
  const qs = new URLSearchParams({ kind: 'object' })
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  if (params?.dataset) qs.set('dataset', params.dataset)
  return apiGet(`/ontologies/${ontologyId}/properties?${qs.toString()}`)
}

export function listDataProperties(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string; dataset?: string },
): Promise<PaginatedResponse<DataProperty>> {
  const qs = new URLSearchParams({ kind: 'data' })
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  if (params?.dataset) qs.set('dataset', params.dataset)
  return apiGet(`/ontologies/${ontologyId}/properties?${qs.toString()}`)
}

export function createObjectProperty(ontologyId: string, data: ObjectPropertyCreate, dataset?: string): Promise<ObjectProperty> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/properties${qs}`, data)
}

export function updateObjectProperty(ontologyId: string, iri: string, data: Partial<ObjectPropertyCreate>, dataset?: string): Promise<ObjectProperty> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPut(`/ontologies/${ontologyId}/properties/${encodeURIComponent(iri)}${qs}`, data)
}

export function createDataProperty(ontologyId: string, data: DataPropertyCreate, dataset?: string): Promise<DataProperty> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/properties${qs}`, data)
}

export function updateDataProperty(ontologyId: string, iri: string, data: Partial<DataPropertyCreate>, dataset?: string): Promise<DataProperty> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPut(`/ontologies/${ontologyId}/properties/${encodeURIComponent(iri)}${qs}`, data)
}

export function deleteProperty(ontologyId: string, iri: string, dataset?: string): Promise<void> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiDelete(`/ontologies/${ontologyId}/properties/${encodeURIComponent(iri)}${qs}`)
}

export function searchRelations(
  ontologyId: string,
  q: string,
  domainIri?: string,
  rangeIri?: string,
  limit = 20,
  dataset?: string,
): Promise<Array<ObjectProperty | DataProperty>> {
  const qs = new URLSearchParams({ q, limit: String(limit) })
  if (domainIri) qs.set('domain_iri', domainIri)
  if (rangeIri) qs.set('range_iri', rangeIri)
  if (dataset) qs.set('dataset', dataset)
  return apiGet(`/ontologies/${ontologyId}/search/relations?${qs.toString()}`)
}
