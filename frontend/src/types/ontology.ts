export interface OntologyStats {
  class_count: number
  individual_count: number
  property_count: number
  triple_count: number
}

export interface Ontology {
  id: string
  name: string
  description?: string
  base_iri: string
  version?: string
  created_at: string
  updated_at: string
  stats: OntologyStats
}

export interface OntologyCreate {
  name: string
  description?: string
  base_iri: string
  version?: string
}

export interface OntologyUpdate {
  name?: string
  description?: string
  version?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface ErrorResponse {
  error: string
  detail?: string
  code?: string
}

export interface JobResponse {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  message?: string
  result?: Record<string, unknown>
}
