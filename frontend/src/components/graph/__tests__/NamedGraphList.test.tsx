import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { mockNamedGraph } from '../../../tests/mocks/handlers'
import { renderWithProviders } from '../../../tests/utils'
import NamedGraphList from '../NamedGraphList'
import { NamedGraphsProvider } from '@/contexts/NamedGraphsContext'

const ONTOLOGY_ID = 'test-ont-uuid'

function renderList({ onImportClick = () => {} } = {}) {
  return renderWithProviders(
    <NamedGraphsProvider>
      <NamedGraphList ontologyId={ONTOLOGY_ID} onImportClick={onImportClick} />
    </NamedGraphsProvider>,
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

  it('loads with all graphs selected by default', async () => {
    renderList()
    await waitFor(() => {
      expect(screen.getByText('1/1 selected')).toBeInTheDocument()
    })
    expect(screen.getByRole('checkbox')).toBeChecked()
    expect(screen.getByRole('button', { name: /deselect all/i })).toBeInTheDocument()
  })

  it('toggles graph checkbox and updates selected counter', async () => {
    renderList()
    fireEvent.click(await screen.findByRole('checkbox'))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /select all/i })).toBeInTheDocument()
    })
  })

  it('deselect all button clears graph selections', async () => {
    renderList()
    fireEvent.click(await screen.findByRole('button', { name: /deselect all/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /select all/i })).toBeInTheDocument()
    })
    expect(screen.getByRole('checkbox')).not.toBeChecked()
  })

  it('shows edit (pencil) button for each graph', async () => {
    renderList()
    await waitFor(() => screen.getByText(mockNamedGraph.iri))
    expect(screen.getByTitle('Edit TTL')).toBeInTheDocument()
  })

  it('clicking edit button opens TTL editor panel', async () => {
    renderList()
    await waitFor(() => screen.getByTitle('Edit TTL'))
    fireEvent.click(screen.getByTitle('Edit TTL'))
    await waitFor(() => {
      expect(screen.getByText(/edit ttl/i)).toBeInTheDocument()
    })
  })

  it('clicking edit button again (toggle) closes the TTL editor panel', async () => {
    renderList()
    await waitFor(() => screen.getByTitle('Edit TTL'))
    fireEvent.click(screen.getByTitle('Edit TTL'))
    await waitFor(() => screen.getByText(/edit ttl/i))

    // Clicking the edit button again toggles the panel closed
    fireEvent.click(screen.getByTitle('Edit TTL'))
    await waitFor(() => {
      expect(screen.queryByText(/edit ttl/i)).not.toBeInTheDocument()
    })
  })
})
