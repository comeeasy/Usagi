export interface ReasonerViolation {
  violation_type: string
  subject_iri: string
  predicate_iri?: string
  object_iri?: string
  message: string
  severity: 'error' | 'warning' | 'info'
}

export interface InferredAxiom {
  subject_iri: string
  predicate_iri: string
  object_iri: string
  inference_rule: string
  confidence: number
}

export interface ReasonerResult {
  ontology_id: string
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  violations: ReasonerViolation[]
  inferred_axioms: InferredAxiom[]
  violation_count: number
  inferred_count: number
  elapsed_seconds?: number
  error?: string
  created_at: string
  completed_at?: string
}

export interface ReasonerJob {
  job_id: string
  ontology_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface ReasonerRunRequest {
  subgraph_iris?: string[]
  include_inferences?: boolean
  check_consistency?: boolean
  reasoner_profile?: 'EL' | 'RL' | 'QL' | 'FULL'
}
