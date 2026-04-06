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

export function executeSparql(ontologyId: string, query: string, dataset?: string): Promise<SparqlResults> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/sparql${qs}`, { query })
}

export function executeSparqlUpdate(ontologyId: string, update: string, dataset?: string): Promise<void> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/sparql/update${qs}`, { update })
}
