import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { mockConcept, mockIndividual } from '../../tests/mocks/handlers'
import { renderWithProviders } from '../../tests/utils'
import EntitiesPage from '../ontology/EntitiesPage'

// GraphCanvas uses cytoscape — mock to avoid jsdom issues
vi.mock('@/components/graph/GraphCanvas', () => ({
  default: ({ elements }: { elements: unknown[] }) => (
    <div data-testid="graph-canvas" data-elements={elements.length} />
  ),
}))

// Mock getConcept for detail panel
vi.mock('@/api/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/entities')>()
  return {
    ...actual,
    getConcept: vi.fn().mockResolvedValue(mockConcept),
    getIndividual: vi.fn().mockResolvedValue(mockIndividual),
  }
})

const ROUTE_PATH = '/:ontologyId/entities'
const INITIAL_ENTRY = '/test-ont-uuid/entities'

function renderEntitiesPage() {
  return renderWithProviders(<EntitiesPage />, {
    initialEntries: [INITIAL_ENTRY],
    path: ROUTE_PATH,
  })
}

describe('EntitiesPage', () => {
  it('renders concepts tab button by default', async () => {
    renderEntitiesPage()
    await waitFor(() => {
      expect(screen.getByText('concepts')).toBeInTheDocument()
    })
  })

  it('shows concept list after loading', async () => {
    renderEntitiesPage()
    await waitFor(() => {
      expect(screen.getByText(mockConcept.label)).toBeInTheDocument()
    })
  })

  it('shows "New Concept" button on concepts tab', async () => {
    renderEntitiesPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /New Concept/i })).toBeInTheDocument()
    })
  })

  it('clicking individuals tab shows New Individual button', async () => {
    renderEntitiesPage()
    await waitFor(() => screen.getByText('individuals'))
    fireEvent.click(screen.getByText('individuals'))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /New Individual/i })).toBeInTheDocument()
    })
  })

  it('opens create form when clicking New Concept', async () => {
    renderEntitiesPage()
    await waitFor(() => screen.getByRole('button', { name: /New Concept/i }))
    fireEvent.click(screen.getByRole('button', { name: /New Concept/i }))
    await waitFor(() => {
      expect(screen.getByText(/Create Concept/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no concepts', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/concepts', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
      ),
    )
    renderEntitiesPage()
    await waitFor(() => {
      expect(screen.queryByText(mockConcept.label)).not.toBeInTheDocument()
    })
  })

  // ── New: embedded graph panel (via Graph tab in EntityRightPanel) ─────

  it('shows Graph tab when a concept is clicked', async () => {
    renderEntitiesPage()
    await waitFor(() => screen.getByText(mockConcept.label))
    fireEvent.click(screen.getByText(mockConcept.label))
    await waitFor(() => {
      // EntityRightPanel shows "graph" tab button
      expect(screen.getByRole('button', { name: /^graph$/i })).toBeInTheDocument()
    })
  })

  it('shows graph canvas after clicking Graph tab', async () => {
    renderEntitiesPage()
    await waitFor(() => screen.getByText(mockConcept.label))
    fireEvent.click(screen.getByText(mockConcept.label))
    await waitFor(() => screen.getByRole('button', { name: /^graph$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^graph$/i }))
    await waitFor(() => {
      expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    })
  })

  it('loads subgraph for the clicked concept IRI', async () => {
    let capturedBody: unknown
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ nodes: [], edges: [] })
      }),
    )
    renderEntitiesPage()
    await waitFor(() => screen.getByText(mockConcept.label))
    fireEvent.click(screen.getByText(mockConcept.label))
    await waitFor(() => screen.getByRole('button', { name: /^graph$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^graph$/i }))
    await waitFor(() => {
      expect((capturedBody as { entity_iris: string[] }).entity_iris).toContain(mockConcept.iri)
    })
  })

  // ── New: individuals sidebar ───────────────────────────────────────────

  it('shows individuals sidebar when a concept is selected', async () => {
    renderEntitiesPage()
    await waitFor(() => screen.getByText(mockConcept.label))
    fireEvent.click(screen.getByText(mockConcept.label))
    await waitFor(() => {
      expect(screen.getByText(mockIndividual.label)).toBeInTheDocument()
    })
  })

  it('hides individuals sidebar when no concept is selected', async () => {
    renderEntitiesPage()
    await waitFor(() => {
      expect(screen.queryByText(mockIndividual.label)).not.toBeInTheDocument()
    })
  })
})
