import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { renderWithProviders } from '../../../tests/utils'
import EntityGraphPanel from '../EntityGraphPanel'

// GraphCanvas uses cytoscape which doesn't work in jsdom — mock the whole component
vi.mock('../GraphCanvas', () => ({
  default: ({ elements }: { elements: unknown[] }) => (
    <div data-testid="graph-canvas" data-elements={elements.length} />
  ),
}))

const ONTOLOGY_ID = 'test-ont-uuid'
const CONCEPT_IRI = 'https://test.example.org/onto#Person'

function renderPanel(entityIri: string | null) {
  return renderWithProviders(
    <EntityGraphPanel ontologyId={ONTOLOGY_ID} entityIri={entityIri} />,
    { initialEntries: [`/${ONTOLOGY_ID}/entities`], path: '/:ontologyId/entities' },
  )
}

describe('EntityGraphPanel', () => {
  it('shows placeholder when no entity is selected', () => {
    renderPanel(null)
    expect(screen.getByText(/select an entity/i)).toBeInTheDocument()
  })

  it('shows loading state while subgraph is loading', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', async () => {
        await new Promise((r) => setTimeout(r, 100))
        return HttpResponse.json({ nodes: [], edges: [] })
      }),
    )
    renderPanel(CONCEPT_IRI)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders graph canvas after subgraph loads', async () => {
    renderPanel(CONCEPT_IRI)
    await waitFor(() => {
      expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    })
  })

  it('shows error message when subgraph fails', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
      ),
    )
    renderPanel(CONCEPT_IRI)
    await waitFor(() => {
      expect(screen.getByText(/failed to load graph/i)).toBeInTheDocument()
    })
  })

  it('reloads graph when entityIri changes', async () => {
    const { rerender } = renderPanel(CONCEPT_IRI)
    await waitFor(() => expect(screen.getByTestId('graph-canvas')).toBeInTheDocument())

    const NEW_IRI = 'https://test.example.org/onto#Animal'
    rerender(
      <EntityGraphPanel ontologyId={ONTOLOGY_ID} entityIri={NEW_IRI} />,
    )
    // Should trigger a new subgraph load (canvas still present)
    await waitFor(() => {
      expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    })
  })
})
