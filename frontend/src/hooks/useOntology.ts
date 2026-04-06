import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listOntologies,
  getOntology,
  createOntology,
  deleteOntology,
} from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import type { OntologyCreate } from '@/types/ontology'

export function useOntologies(page = 1, pageSize = 20) {
  const { dataset } = useDataset()
  return useQuery({
    queryKey: ['ontologies', page, pageSize, dataset],
    queryFn: () => listOntologies({ page, pageSize, dataset }),
  })
}

export function useOntology(id: string | undefined) {
  const { dataset } = useDataset()
  return useQuery({
    queryKey: ['ontologies', id, dataset],
    queryFn: () => getOntology(id!, dataset),
    enabled: !!id,
  })
}

export function useCreateOntology() {
  const queryClient = useQueryClient()
  const { dataset } = useDataset()
  return useMutation({
    mutationFn: (data: OntologyCreate) => createOntology(data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontologies'] })
    },
  })
}

export function useDeleteOntology() {
  const queryClient = useQueryClient()
  const { dataset } = useDataset()
  return useMutation({
    mutationFn: (id: string) => deleteOntology(id, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontologies'] })
    },
  })
}
