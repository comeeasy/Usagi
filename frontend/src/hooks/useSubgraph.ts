import { useMutation } from '@tanstack/react-query'
import { getSubgraph } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'

interface SubgraphParams {
  rootIris?: string[]
  depth?: number
  includeIndividuals?: boolean
}

export function useSubgraph(ontologyId: string | undefined) {
  const { dataset } = useDataset()
  return useMutation({
    mutationFn: (params: SubgraphParams) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      return getSubgraph(ontologyId, { ...params, dataset })
    },
  })
}
