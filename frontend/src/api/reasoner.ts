// Reasoner API client stubs

import { apiGet, apiPost } from './client'
import type { ReasonerResult, ReasonerJob } from '@/types/reasoner'

// TODO: implement all functions

export function runReasoner(
  ontologyId: string,
  request: {
    subgraph_iris?: string[]
    include_inferences?: boolean
    check_consistency?: boolean
    reasoner_profile?: string
  },
): Promise<ReasonerJob> {
  // TODO: return apiPost(`/ontologies/${ontologyId}/reasoner/run`, request)
  throw new Error('Not implemented')
}

export function getReasonerResult(jobId: string): Promise<ReasonerResult> {
  // TODO: return apiGet(`/reasoner/jobs/${jobId}`)
  throw new Error('Not implemented')
}

export function listReasonerJobs(ontologyId: string): Promise<ReasonerJob[]> {
  // TODO: return apiGet(`/ontologies/${ontologyId}/reasoner/jobs`)
  throw new Error('Not implemented')
}
