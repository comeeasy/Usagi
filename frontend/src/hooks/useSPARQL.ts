import { useMutation } from '@tanstack/react-query'
import { executeSparql } from '@/api/sparql'
import { useDataset } from '@/contexts/DatasetContext'

export function useSPARQL(ontologyId: string | undefined) {
  const { dataset } = useDataset()
  return useMutation({
    mutationFn: (query: string) => {
      if (!ontologyId) throw new Error('ontologyId is required')
      return executeSparql(ontologyId, query, dataset)
    },
  })
}
