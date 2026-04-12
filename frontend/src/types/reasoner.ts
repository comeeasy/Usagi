export interface ReasonerViolation {
  type: 'UnsatisfiableClass' | 'CardinalityViolation' | 'DisjointViolation' | 'DomainRangeViolation'
  subject_iri: string
  description: string
}

export interface InferredAxiom {
  subject: string
  predicate: string
  object: string
  inference_rule: string
}

export interface ReasonerResultData {
  consistent: boolean
  violations: ReasonerViolation[]
  inferred_axioms: InferredAxiom[]
  execution_ms: number
}

export interface ReasonerResult {
  job_id: string
  ontology_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  result?: ReasonerResultData
  error?: string
}

export interface ReasonerJob {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

export interface ReasonerRunRequest {
  subgraph_entity_iris?: string[]
  include_inferences?: boolean
  check_consistency?: boolean
  reasoner_profile?: 'OWL_DL' | 'OWL_EL' | 'OWL_RL' | 'OWL_QL'
}
