// TODO: useMutation으로 서브그래프 쿼리
// getSubgraph(ontologyId, params) → { nodes, edges } (Cytoscape 형식)
// 필터: concept IRIs, depth, include individuals

import { useMutation } from '@tanstack/react-query'
// TODO: import { getSubgraph } from '@/api/ontologies'

interface SubgraphParams {
  rootIris?: string[]
  depth?: number
  includeIndividuals?: boolean
}

export function useSubgraph(ontologyId: string | undefined) {
  return useMutation({
    mutationFn: async (params: SubgraphParams) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      // TODO: return getSubgraph(ontologyId, params)
      throw new Error('Not implemented')
    },
  })
}
