// Reasoner API client

import { apiGet, apiPost } from './client'
import type { ReasonerResult, ReasonerJob, ReasonerRunRequest } from '@/types/reasoner'

export function runReasoner(
  ontologyId: string,
  request: ReasonerRunRequest,
  dataset?: string,
): Promise<ReasonerJob> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/reasoner/run${qs}`, request)
}

export function getReasonerResult(ontologyId: string, jobId: string): Promise<ReasonerResult> {
  return apiGet(`/ontologies/${ontologyId}/reasoner/jobs/${jobId}`)
}

export function listReasonerJobs(ontologyId: string): Promise<ReasonerJob[]> {
  return apiGet(`/ontologies/${ontologyId}/reasoner/jobs`)
}
