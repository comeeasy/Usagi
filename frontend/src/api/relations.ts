// Relations (ObjectProperty / DataProperty) API client stubs

import { apiGet, apiPost, apiPut, apiDelete } from './client'
import type { ObjectProperty, DataProperty, ObjectPropertyCreate, DataPropertyCreate } from '@/types/property'
import type { PaginatedResponse } from '@/types/ontology'

// TODO: implement all functions

export function listObjectProperties(
  ontologyId: string,
  params?: { page?: number; pageSize?: number },
): Promise<PaginatedResponse<ObjectProperty>> {
  return apiGet(`/ontologies/${ontologyId}/properties/object`)
}

export function listDataProperties(
  ontologyId: string,
  params?: { page?: number; pageSize?: number },
): Promise<PaginatedResponse<DataProperty>> {
  return apiGet(`/ontologies/${ontologyId}/properties/data`)
}

export function createObjectProperty(ontologyId: string, data: ObjectPropertyCreate): Promise<ObjectProperty> {
  return apiPost(`/ontologies/${ontologyId}/properties/object`, data)
}

export function createDataProperty(ontologyId: string, data: DataPropertyCreate): Promise<DataProperty> {
  return apiPost(`/ontologies/${ontologyId}/properties/data`, data)
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
): Promise<unknown[]> {
  // TODO: return apiGet(`/ontologies/${ontologyId}/search/relations?q=${q}&...`)
  throw new Error('Not implemented')
}
