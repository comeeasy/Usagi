import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchEntities, vectorSearch } from '@/api/entities'

export function useEntitySearch(
  ontologyId: string | undefined,
  initialQuery = '',
  kind: string = 'all',
  useVector = false,
) {
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(initialQuery), 300)
    return () => clearTimeout(timer)
  }, [initialQuery])

  return useQuery({
    queryKey: ['entities', ontologyId, debouncedQuery, kind, useVector],
    queryFn: () => {
      if (useVector) return vectorSearch(ontologyId!, debouncedQuery)
      return searchEntities(ontologyId!, debouncedQuery, kind)
    },
    enabled: !!ontologyId && debouncedQuery.length > 0,
  })
}

export function useSearchRelations(
  ontologyId: string | undefined,
  query: string,
  domainIri?: string,
  rangeIri?: string,
) {
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  return useQuery({
    queryKey: ['relations-search', ontologyId, debouncedQuery, domainIri, rangeIri],
    queryFn: async () => {
      const { searchRelations } = await import('@/api/relations')
      return searchRelations(ontologyId!, debouncedQuery, domainIri, rangeIri)
    },
    enabled: !!ontologyId && debouncedQuery.length > 0,
  })
}
