import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { renderWithProviders } from '@/tests/utils'
import { server } from '@/tests/mocks/server'
import { DatasetProvider } from '@/contexts/DatasetContext'
import { NamedGraphsProvider } from '@/contexts/NamedGraphsContext'
import ConceptGraphPanel from '../ConceptGraphPanel'

const ONTOLOGY_ID = 'test-ont-uuid'

vi.mock('@/components/graph/GraphCanvas', () => ({
  default: ({ elements }: { elements: unknown[] }) => (
    <div data-testid="graph-canvas" data-elements={elements.length} />
  ),
}))

function renderPanel() {
  return renderWithProviders(
    <DatasetProvider>
      <NamedGraphsProvider>
        <ConceptGraphPanel ontologyId={ONTOLOGY_ID} />
      </NamedGraphsProvider>
    </DatasetProvider>,
    { initialEntries: [`/${ONTOLOGY_ID}/schema`], path: '/:ontologyId/schema' },
  )
}

describe('ConceptGraphPanel', () => {
  it('concepts/properties 요청에 page_size=100을 사용한다', async () => {
    const seen: { concepts?: string; properties?: string } = {}

    server.use(
      http.get('/api/v1/ontologies/:id/concepts', ({ request }) => {
        const url = new URL(request.url)
        seen.concepts = url.searchParams.get('page_size') ?? ''
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 100 })
      }),
      http.get('/api/v1/ontologies/:id/properties', ({ request }) => {
        const url = new URL(request.url)
        seen.properties = url.searchParams.get('page_size') ?? ''
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 100 })
      }),
    )

    renderPanel()

    await waitFor(() => {
      expect(seen.concepts).toBeDefined()
      expect(seen.properties).toBeDefined()
    })

    expect(seen.concepts).toBe('100')
    expect(seen.properties).toBe('100')
    expect(screen.getByText(/no concepts to display/i)).toBeInTheDocument()
  })
})
