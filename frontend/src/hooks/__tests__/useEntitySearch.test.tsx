import { describe, it, expect, vi } from 'vitest'
import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DatasetProvider } from '@/contexts/DatasetContext'
import { NamedGraphsProvider, useNamedGraphs } from '@/contexts/NamedGraphsContext'
import { useEntitySearch } from '../useEntitySearch'

const searchEntitiesMock = vi.fn(async (_ontologyId: string, q: string, _kind?: string, _limit?: number, _dataset?: string, graphIris?: string[]) => {
  const byGraph: Record<string, Array<{ iri: string; label: string; kind: 'concept' }>> = {
    'urn:graph:A': [{ iri: 'https://example.org/concepts/A', label: `${q}-A`, kind: 'concept' }],
    'urn:graph:B': [{ iri: 'https://example.org/concepts/B', label: `${q}-B`, kind: 'concept' }],
  }
  const selected = graphIris?.[0] ?? 'urn:graph:A'
  return byGraph[selected] ?? []
})

vi.mock('@/api/entities', () => ({
  searchEntities: (...args: unknown[]) => searchEntitiesMock(...args),
  vectorSearch: vi.fn(),
}))

function GraphSelectionInitializer({ selected }: { selected: string[] }) {
  const { setKnownGraphs, deselectAll, toggleGraph } = useNamedGraphs()

  useEffect(() => {
    setKnownGraphs(['urn:graph:A', 'urn:graph:B'])
    deselectAll()
    selected.forEach((iri) => toggleGraph(iri))
  }, [deselectAll, selected, setKnownGraphs, toggleGraph])

  return null
}

function makeWrapper(selected: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <DatasetProvider>
          <NamedGraphsProvider>
            <GraphSelectionInitializer selected={selected} />
            {children}
          </NamedGraphsProvider>
        </DatasetProvider>
      </QueryClientProvider>
    )
  }
}

describe('useEntitySearch graph filter', () => {
  it('선택된 graph_iris 기준으로 검색 결과를 받는다', async () => {
    const wrapper = makeWrapper(['urn:graph:B'])

    const { result } = renderHook(() => useEntitySearch('ont-1', 'alice', 'all', false), { wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    }, { timeout: 3000 })

    expect(searchEntitiesMock).toHaveBeenCalled()
    expect(searchEntitiesMock.mock.calls.at(-1)?.[5]).toEqual(['urn:graph:B'])
    expect(result.current.data?.[0]?.label).toBe('alice-B')
  })
})
