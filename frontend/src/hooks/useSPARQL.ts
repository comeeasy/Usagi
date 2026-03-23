// TODO: useMutation으로 SPARQL 실행
// executeSparql(ontologyId, query) → SparqlResults
// 에러 상태 관리

import { useMutation } from '@tanstack/react-query'
// TODO: import { executeSparql } from '@/api/sparql'

export function useSPARQL(ontologyId: string | undefined) {
  return useMutation({
    mutationFn: async (query: string) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      // TODO: return executeSparql(ontologyId, query)
      throw new Error('Not implemented')
    },
  })
}
