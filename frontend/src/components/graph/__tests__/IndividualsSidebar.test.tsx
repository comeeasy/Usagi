import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { mockIndividual, mockConcept } from '../../../tests/mocks/handlers'
import { renderWithProviders } from '../../../tests/utils'
import IndividualsSidebar from '../IndividualsSidebar'

const ONTOLOGY_ID = 'test-ont-uuid'

function renderSidebar(conceptIri: string | null) {
  return renderWithProviders(
    <IndividualsSidebar ontologyId={ONTOLOGY_ID} conceptIri={conceptIri} />,
    { initialEntries: [`/${ONTOLOGY_ID}/entities`], path: '/:ontologyId/entities' },
  )
}

describe('IndividualsSidebar', () => {
  it('renders nothing meaningful when no concept is selected', () => {
    const { container } = renderSidebar(null)
    expect(container.firstChild).toBeNull()
  })

  it('shows loading spinner while fetching individuals', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/individuals', async () => {
        await new Promise((r) => setTimeout(r, 100))
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 })
      }),
    )
    renderSidebar(mockConcept.iri)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows individuals for the selected concept', async () => {
    renderSidebar(mockConcept.iri)
    await waitFor(() => {
      expect(screen.getByText(mockIndividual.label)).toBeInTheDocument()
    })
  })

  it('shows individual count', async () => {
    renderSidebar(mockConcept.iri)
    await waitFor(() => {
      expect(screen.getByText(/1/)).toBeInTheDocument()
    })
  })

  it('shows empty state when concept has no individuals', async () => {
    server.use(
      http.get('/api/v1/ontologies/:id/individuals', ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('class_iri')) {
          return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 })
        }
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 })
      }),
    )
    renderSidebar(mockConcept.iri)
    await waitFor(() => {
      expect(screen.getByText(/no individuals/i)).toBeInTheDocument()
    })
  })
})
