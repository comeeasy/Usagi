import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listOntologies,
  getOntology,
  createOntology,
  deleteOntology,
} from '@/api/ontologies'
import type { OntologyCreate } from '@/types/ontology'

export function useOntologies(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['ontologies', page, pageSize],
    queryFn: () => listOntologies({ page, pageSize }),
  })
}

export function useOntology(id: string | undefined) {
  return useQuery({
    queryKey: ['ontologies', id],
    queryFn: () => getOntology(id!),
    enabled: !!id,
  })
}

export function useCreateOntology() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: OntologyCreate) => createOntology(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontologies'] })
    },
  })
}

export function useDeleteOntology() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteOntology(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontologies'] })
    },
  })
}
