import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { mockObjectProperty, mockDataProperty } from '../../tests/mocks/handlers'
import { renderWithProviders } from '../../tests/utils'
import RelationsPage from '../ontology/RelationsPage'

const ROUTE_PATH = '/:ontologyId/relations'
const INITIAL_ENTRY = '/test-ont-uuid/relations'

function renderRelationsPage() {
  return renderWithProviders(<RelationsPage />, {
    initialEntries: [INITIAL_ENTRY],
    path: ROUTE_PATH,
  })
}

describe('RelationsPage', () => {
  it('renders object Properties tab button by default', async () => {
    renderRelationsPage()
    await waitFor(() => {
      expect(screen.getByText('object Properties')).toBeInTheDocument()
    })
  })

  it('renders data Properties tab button', async () => {
    renderRelationsPage()
    await waitFor(() => {
      expect(screen.getByText('data Properties')).toBeInTheDocument()
    })
  })

  it('shows New Property button', async () => {
    renderRelationsPage()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /New Property/i })).toBeInTheDocument()
    })
  })

  it('shows object property list on default tab', async () => {
    renderRelationsPage()
    await waitFor(() => {
      expect(screen.getByText(mockObjectProperty.label)).toBeInTheDocument()
    })
  })

  it('clicking data Properties tab shows data properties', async () => {
    renderRelationsPage()
    await waitFor(() => screen.getByText('data Properties'))
    fireEvent.click(screen.getByText('data Properties'))
    await waitFor(() => {
      expect(screen.getByText(mockDataProperty.label)).toBeInTheDocument()
    })
  })

  it('opens create form when clicking New Property', async () => {
    renderRelationsPage()
    await waitFor(() => screen.getByRole('button', { name: /New Property/i }))
    fireEvent.click(screen.getByRole('button', { name: /New Property/i }))
    await waitFor(() => {
      expect(screen.getByText(/Create Property/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no object properties', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/properties/object', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
      ),
    )
    renderRelationsPage()
    await waitFor(() => {
      expect(screen.queryByText(mockObjectProperty.label)).not.toBeInTheDocument()
    })
  })
})
