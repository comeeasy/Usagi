// TODO: useQuery로 온톨로지 목록/상세 조회
// useOntologies(): 전체 목록 + 페이지네이션
// useOntology(id): 단건 조회
// useOntologyStats(id): 통계 조회

import { useQuery } from '@tanstack/react-query'
// TODO: import { listOntologies, getOntology } from '@/api/ontologies'

export function useOntologies(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['ontologies', page, pageSize],
    queryFn: async () => {
      // TODO: return listOntologies({ page, pageSize })
      throw new Error('Not implemented')
    },
  })
}

export function useOntology(id: string | undefined) {
  return useQuery({
    queryKey: ['ontologies', id],
    queryFn: async () => {
      // TODO: return getOntology(id!)
      throw new Error('Not implemented')
    },
    enabled: !!id,
  })
}
