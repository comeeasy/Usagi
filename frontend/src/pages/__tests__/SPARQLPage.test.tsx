import { describe, it, expect } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { renderWithProviders } from '../../tests/utils'
import SPARQLPage from '../ontology/SPARQLPage'

const ROUTE_PATH = '/:ontologyId/sparql'
const INITIAL_ENTRY = '/test-ont-uuid/sparql'

function renderSPARQLPage() {
  return renderWithProviders(<SPARQLPage />, {
    initialEntries: [INITIAL_ENTRY],
    path: ROUTE_PATH,
  })
}

describe('SPARQLPage', () => {
  it('renders SPARQL Query heading', () => {
    renderSPARQLPage()
    expect(screen.getByText('SPARQL Query')).toBeInTheDocument()
  })

  it('renders editor toolbar with Run button', () => {
    renderSPARQLPage()
    expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument()
  })

  it('renders description text', () => {
    renderSPARQLPage()
    expect(screen.getByText(/Query the ontology using SPARQL 1\.1/i)).toBeInTheDocument()
  })

  it('shows query results after clicking Run', async () => {
    renderSPARQLPage()
    fireEvent.click(screen.getByRole('button', { name: /run/i }))
    await waitFor(() => {
      expect(screen.getByText('1 result')).toBeInTheDocument()
    })
  })

  it('shows column header from SPARQL variables', async () => {
    renderSPARQLPage()
    fireEvent.click(screen.getByRole('button', { name: /run/i }))
    await waitFor(() => {
      expect(screen.getByText('?c')).toBeInTheDocument()
    })
  })

  it('shows error message when API returns error', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/sparql', () =>
        HttpResponse.json({ detail: 'SPARQL parse error' }, { status: 400 }),
      ),
    )
    renderSPARQLPage()
    fireEvent.click(screen.getByRole('button', { name: /run/i }))
    await waitFor(() => {
      expect(screen.getByText(/query error/i)).toBeInTheDocument()
    })
  })
})
