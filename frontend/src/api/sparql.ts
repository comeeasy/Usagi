// SPARQL API client stubs

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
  // TODO: return apiPost(`/ontologies/${ontologyId}/sparql`, { query })
  throw new Error('Not implemented')
}

export function executeSparqlUpdate(ontologyId: string, update: string): Promise<void> {
  // TODO: return apiPost(`/ontologies/${ontologyId}/sparql/update`, { update })
  throw new Error('Not implemented')
}
