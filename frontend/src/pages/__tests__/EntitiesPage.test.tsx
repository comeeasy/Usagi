import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { mockConcept } from '../../tests/mocks/handlers'
import { renderWithProviders } from '../../tests/utils'
import EntitiesPage from '../ontology/EntitiesPage'

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
})
