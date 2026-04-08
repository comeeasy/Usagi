import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchEntities, vectorSearch } from '@/api/entities'
import { useDataset } from '@/contexts/DatasetContext'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'

export function useEntitySearch(
  ontologyId: string | undefined,
  initialQuery = '',
  kind: string = 'all',
  useVector = false,
) {
  const { dataset } = useDataset()
  const { selectedGraphIris } = useNamedGraphs()
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(initialQuery), 300)
    return () => clearTimeout(timer)
  }, [initialQuery])

  return useQuery({
    queryKey: ['entities', ontologyId, debouncedQuery, kind, useVector, dataset, selectedGraphIris],
    queryFn: async () => {
      if (!useVector) return searchEntities(ontologyId!, debouncedQuery, kind, 20, dataset, selectedGraphIris)

      // Vector ON: keyword + vector 병렬 호출 후 병합 (IRI 중복 제거, keyword 결과 우선)
      const [keywordResults, vectorResults] = await Promise.all([
        searchEntities(ontologyId!, debouncedQuery, kind, 20, dataset, selectedGraphIris),
        vectorSearch(ontologyId!, debouncedQuery, 10, dataset),
      ])
      const seen = new Set(keywordResults.map((r) => r.iri))
      const extra = vectorResults.filter((r) => !seen.has(r.iri))
      return [...keywordResults, ...extra]
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
  const { dataset } = useDataset()
  const { selectedGraphIris } = useNamedGraphs()
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  return useQuery({
    queryKey: ['relations-search', ontologyId, debouncedQuery, domainIri, rangeIri, dataset, selectedGraphIris],
    queryFn: async () => {
      const { searchRelations } = await import('@/api/relations')
      return searchRelations(ontologyId!, debouncedQuery, domainIri, rangeIri, 20, dataset, selectedGraphIris)
    },
    enabled: !!ontologyId && debouncedQuery.length > 0,
  })
}
