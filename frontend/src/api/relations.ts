// Relations (ObjectProperty / DataProperty) API client

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { ObjectProperty, DataProperty, ObjectPropertyCreate, DataPropertyCreate } from '@/types/property'
import type { PaginatedResponse } from '@/types/ontology'

export function listObjectProperties(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string },
): Promise<PaginatedResponse<ObjectProperty>> {
  const qs = new URLSearchParams({ kind: 'object' })
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  return apiGet(`/ontologies/${ontologyId}/properties?${qs.toString()}`)
}

export function listDataProperties(
  ontologyId: string,
  params?: { page?: number; pageSize?: number; search?: string },
): Promise<PaginatedResponse<DataProperty>> {
  const qs = new URLSearchParams({ kind: 'data' })
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.search) qs.set('search', params.search)
  return apiGet(`/ontologies/${ontologyId}/properties?${qs.toString()}`)
}

export function createObjectProperty(ontologyId: string, data: ObjectPropertyCreate): Promise<ObjectProperty> {
  return apiPost(`/ontologies/${ontologyId}/properties`, data)
}

export function updateObjectProperty(ontologyId: string, iri: string, data: Partial<ObjectPropertyCreate>): Promise<ObjectProperty> {
  return apiPut(`/ontologies/${ontologyId}/properties/${encodeURIComponent(iri)}`, data)
}

export function createDataProperty(ontologyId: string, data: DataPropertyCreate): Promise<DataProperty> {
  return apiPost(`/ontologies/${ontologyId}/properties`, data)
}

export function updateDataProperty(ontologyId: string, iri: string, data: Partial<DataPropertyCreate>): Promise<DataProperty> {
  return apiPut(`/ontologies/${ontologyId}/properties/${encodeURIComponent(iri)}`, data)
}

export function deleteProperty(ontologyId: string, iri: string): Promise<void> {
  return apiDelete(`/ontologies/${ontologyId}/properties/${encodeURIComponent(iri)}`)
}

export function searchRelations(
  ontologyId: string,
  q: string,
  domainIri?: string,
  rangeIri?: string,
  limit = 20,
): Promise<Array<ObjectProperty | DataProperty>> {
  const qs = new URLSearchParams({ q, limit: String(limit) })
  if (domainIri) qs.set('domain_iri', domainIri)
  if (rangeIri) qs.set('range_iri', rangeIri)
  return apiGet(`/ontologies/${ontologyId}/search/relations?${qs.toString()}`)
}
