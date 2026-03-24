import { useMutation } from '@tanstack/react-query'
import { getSubgraph } from '@/api/ontologies'

interface SubgraphParams {
  rootIris?: string[]
  depth?: number
  includeIndividuals?: boolean
}

export function useSubgraph(ontologyId: string | undefined) {
  return useMutation({
    mutationFn: (params: SubgraphParams) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      return getSubgraph(ontologyId, params)
    },
  })
}
