import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { mockNamedGraph } from '../../tests/mocks/handlers'
import { renderWithProviders } from '../../tests/utils'
import GraphPage from '../ontology/GraphPage'

// GraphCanvas uses cytoscape — mock it to avoid jsdom issues
vi.mock('@/components/graph/GraphCanvas', () => ({
  default: ({ elements }: { elements: unknown[] }) => (
    <div data-testid="graph-canvas" data-elements={elements.length} />
  ),
}))

const ROUTE_PATH = '/:ontologyId/graph'
const INITIAL_ENTRY = '/test-ont-uuid/graph'

function renderGraphPage() {
  return renderWithProviders(<GraphPage />, {
    initialEntries: [INITIAL_ENTRY],
    path: ROUTE_PATH,
  })
}

describe('GraphPage (named graph list)', () => {
  it('shows named graph list after loading', async () => {
    renderGraphPage()
    await waitFor(() => {
      expect(screen.getByText(mockNamedGraph.iri)).toBeInTheDocument()
    })
  })

  it('shows Import button', async () => {
    renderGraphPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument()
    })
  })

  it('clicking Import button opens import section', async () => {
    renderGraphPage()
    await waitFor(() => screen.getByRole('button', { name: /import/i }))
    fireEvent.click(screen.getByRole('button', { name: /import/i }))
    await waitFor(() => {
      // ImportPanel renders mode selector with Standard option
      expect(screen.getByText(/standard/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no graphs exist', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/graphs', () => HttpResponse.json([])),
    )
    renderGraphPage()
    await waitFor(() => {
      expect(screen.getByText(/no graphs/i)).toBeInTheDocument()
    })
  })

  it('shows source info for imported graphs', async () => {
    renderGraphPage()
    await waitFor(() => {
      expect(screen.getByText(mockNamedGraph.source_label!)).toBeInTheDocument()
    })
  })
})
