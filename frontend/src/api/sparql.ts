// SPARQL API client

import { apiPost } from './client'

export interface SparqlBinding {
  type: 'uri' | 'literal' | 'bnode'
  value: string
  datatype?: string
  'xml:lang'?: string
}

export interface SparqlResults {
  variables: string[]
  bindings: Record<string, SparqlBinding>[]
}

export function executeSparql(ontologyId: string, query: string): Promise<SparqlResults> {
  return apiPost(`/ontologies/${ontologyId}/sparql`, { query })
}

export function executeSparqlUpdate(ontologyId: string, update: string): Promise<void> {
  return apiPost(`/ontologies/${ontologyId}/sparql/update`, { update })
}
