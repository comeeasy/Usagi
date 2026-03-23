// TODO: useQuery + debounce로 Entity 검색
// 키워드 debounce (300ms), kind 필터, 벡터 검색 모드 토글
// searchEntities / vectorSearch API 호출

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
// TODO: import { searchEntities, vectorSearch } from '@/api/entities'

export function useEntitySearch(
  ontologyId: string | undefined,
  initialQuery = '',
  kind: string = 'all',
  useVector = false,
) {
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery)

  useEffect(() => {
    // TODO: implement debounce
    // const timer = setTimeout(() => setDebouncedQuery(initialQuery), 300)
    // return () => clearTimeout(timer)
    setDebouncedQuery(initialQuery)
  }, [initialQuery])

  return useQuery({
    queryKey: ['entities', ontologyId, debouncedQuery, kind, useVector],
    queryFn: async () => {
      // TODO: if (useVector) return vectorSearch(ontologyId!, debouncedQuery)
      // TODO: return searchEntities(ontologyId!, debouncedQuery, kind)
      throw new Error('Not implemented')
    },
    enabled: !!ontologyId && debouncedQuery.length > 0,
  })
}
