import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { runReasoner, getReasonerResult } from '@/api/reasoner'
import type { ReasonerRunRequest } from '@/types/reasoner'

export function useReasoner(ontologyId: string | undefined) {
  const [jobId, setJobId] = useState<string | null>(null)

  const runMutation = useMutation({
    mutationFn: (request: ReasonerRunRequest) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      return runReasoner(ontologyId, request)
    },
    onSuccess: (job) => {
      setJobId(job.job_id)
    },
  })

  const resultQuery = useQuery({
    queryKey: ['reasoner', 'result', jobId],
    queryFn: () => getReasonerResult(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const result = query.state.data
      if (result?.status === 'completed' || result?.status === 'failed') return false
      return 1000
    },
  })

  return { runMutation, resultQuery, jobId }
}
