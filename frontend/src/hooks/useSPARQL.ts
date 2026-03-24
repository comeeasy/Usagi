import { useMutation } from '@tanstack/react-query'
import { executeSparql } from '@/api/sparql'

export function useSPARQL(ontologyId: string | undefined) {
  return useMutation({
    mutationFn: (query: string) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      return executeSparql(ontologyId, query)
    },
  })
}
