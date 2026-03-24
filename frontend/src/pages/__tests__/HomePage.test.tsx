import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../tests/mocks/server'
import { mockOntology } from '../../tests/mocks/handlers'
import { renderWithProviders } from '../../tests/utils'
import HomePage from '../HomePage'

describe('HomePage', () => {
  it('shows loading spinner initially', () => {
    renderWithProviders(<HomePage />)
    expect(document.querySelector('svg')).toBeInTheDocument()
  })

  it('renders ontology cards after loading', async () => {
    renderWithProviders(<HomePage />)
    await waitFor(() => {
      expect(screen.getByText(mockOntology.name)).toBeInTheDocument()
    })
  })

  it('shows "New Ontology" button', async () => {
    renderWithProviders(<HomePage />)
    await waitFor(() => {
      expect(screen.getByText('New Ontology')).toBeInTheDocument()
    })
  })

  it('opens create modal when clicking "New Ontology"', async () => {
    renderWithProviders(<HomePage />)
    await waitFor(() => screen.getByText('New Ontology'))
    fireEvent.click(screen.getByText('New Ontology'))
    await waitFor(() => {
      expect(screen.getByPlaceholderText('My Ontology')).toBeInTheDocument()
    })
  })

  it('shows empty state when no ontologies', async () => {
    server.use(
      http.get('/api/v1/ontologies', () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
      ),
    )
    renderWithProviders(<HomePage />)
    await waitFor(() => {
      expect(screen.getByText(/no ontologies yet/i)).toBeInTheDocument()
    })
  })

  it('shows error message on API failure', async () => {
    server.use(
      http.get('/api/v1/ontologies', () => HttpResponse.error()),
    )
    renderWithProviders(<HomePage />)
    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })
})
