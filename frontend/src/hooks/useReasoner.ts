// TODO: useMutation + polling으로 추론 실행/결과 조회
// runReasoner(ontologyId, request) → JobResponse
// pollReasonerResult(jobId) → ReasonerResult (1초 interval polling)
// completed/failed 시 polling 중단

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
// TODO: import { runReasoner, getReasonerResult } from '@/api/reasoner'

export function useReasoner(ontologyId: string | undefined) {
  const [jobId, setJobId] = useState<string | null>(null)

  const runMutation = useMutation({
    mutationFn: async (request: unknown) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      // TODO: const job = await runReasoner(ontologyId, request)
      // setJobId(job.job_id)
      // return job
      throw new Error('Not implemented')
    },
  })

  const resultQuery = useQuery({
    queryKey: ['reasoner', 'result', jobId],
    queryFn: async () => {
      // TODO: return getReasonerResult(jobId!)
      throw new Error('Not implemented')
    },
    enabled: !!jobId,
    refetchInterval: (data: unknown) => {
      // TODO: stop polling when completed/failed
      // const result = data as ReasonerResult | undefined
      // if (result?.status === 'completed' || result?.status === 'failed') return false
      return 1000
    },
  })

  return { runMutation, resultQuery, jobId }
}
