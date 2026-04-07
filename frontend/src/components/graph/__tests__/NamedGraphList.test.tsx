import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { mockNamedGraph } from '../../../tests/mocks/handlers'
import { renderWithProviders } from '../../../tests/utils'
import NamedGraphList from '../NamedGraphList'

const ONTOLOGY_ID = 'test-ont-uuid'

function renderList({ onImportClick = () => {} } = {}) {
  return renderWithProviders(
    <NamedGraphList ontologyId={ONTOLOGY_ID} onImportClick={onImportClick} />,
    { initialEntries: [`/${ONTOLOGY_ID}/graph`], path: '/:ontologyId/graph' },
  )
}

describe('NamedGraphList', () => {
  it('shows loading state initially', () => {
    renderList()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders graph IRI after loading', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText(mockNamedGraph.iri)).toBeInTheDocument()
    })
  })

  it('shows triple count for each graph', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText(new RegExp(`${mockNamedGraph.triple_count}`))).toBeInTheDocument()
    })
  })

  it('shows source label for graphs with source info', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText(mockNamedGraph.source_label!)).toBeInTheDocument()
    })
  })

  it('shows source type badge', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText(/url/i)).toBeInTheDocument()
    })
  })

  it('shows "Import" button', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /import/i })).toBeInTheDocument()
    })
  })

  it('calls onImportClick when Import button is clicked', async () => {
    const onImportClick = vi.fn()
    renderList({ onImportClick })
    await waitFor(() => screen.getByRole('button', { name: /import/i }))
    fireEvent.click(screen.getByRole('button', { name: /import/i }))
    expect(onImportClick).toHaveBeenCalledOnce()
  })

  it('shows empty state when no graphs exist', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/graphs', () => HttpResponse.json([])),
    )
    renderList()
    await waitFor(() => {
      expect(screen.getByText(/no graphs/i)).toBeInTheDocument()
    })
  })

  it('shows "unknown" source for graphs without source info', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/graphs', () =>
        HttpResponse.json([{ iri: 'https://example.org/g', triple_count: 5, source_type: null, source_label: null }]),
      ),
    )
    renderList()
    await waitFor(() => {
      expect(screen.getByText(/manual/i)).toBeInTheDocument()
    })
  })
})
