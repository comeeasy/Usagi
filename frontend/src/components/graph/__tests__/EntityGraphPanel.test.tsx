import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { renderWithProviders } from '../../../tests/utils'
import EntityGraphPanel from '../EntityGraphPanel'

// GraphCanvas uses cytoscape which doesn't work in jsdom — mock the whole component
vi.mock('../GraphCanvas', () => ({
  default: ({ elements }: { elements: Array<{ data: { label?: string } }> }) => (
    <div
      data-testid="graph-canvas"
      data-elements={elements.length}
      data-labels={elements.map((e) => e.data.label ?? '').join('|')}
    />
  ),
}))

const ONTOLOGY_ID = 'test-ont-uuid'
const CONCEPT_IRI = 'https://test.example.org/onto#Person'
const ANIMAL_IRI = 'https://test.example.org/onto#Animal'

function renderPanel(entityIris: string[]) {
  const onRemoveIri = vi.fn()
  return {
    onRemoveIri,
    ...renderWithProviders(
      <EntityGraphPanel ontologyId={ONTOLOGY_ID} entityIris={entityIris} onRemoveIri={onRemoveIri} />,
      { initialEntries: [`/${ONTOLOGY_ID}/entities`], path: '/:ontologyId/entities' },
    ),
  }
}

describe('EntityGraphPanel', () => {
  it('shows placeholder when no entity is selected', () => {
    renderPanel([])
    expect(screen.getByText(/select an entity/i)).toBeInTheDocument()
  })

  it('shows loading state while subgraph is loading', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', async () => {
        await new Promise((r) => setTimeout(r, 100))
        return HttpResponse.json({ nodes: [], edges: [] })
      }),
    )
    renderPanel([CONCEPT_IRI])
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders graph canvas after subgraph loads', async () => {
    renderPanel([CONCEPT_IRI])
    await waitFor(() => {
      expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    })
  })

  it('shows chip for each selected entity', async () => {
    renderPanel([CONCEPT_IRI, ANIMAL_IRI])
    await waitFor(() => {
      expect(screen.getByText('Person')).toBeInTheDocument()
      expect(screen.getByText('Animal')).toBeInTheDocument()
    })
  })

  it('calls onRemoveIri when chip × is clicked', async () => {
    const { onRemoveIri } = renderPanel([CONCEPT_IRI])
    await waitFor(() => screen.getByText('Person'))
    fireEvent.click(screen.getAllByRole('button').find(b => b.closest('span'))!)
    expect(onRemoveIri).toHaveBeenCalledWith(CONCEPT_IRI)
  })

  it('shows error message when subgraph fails', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
      ),
    )
    renderPanel([CONCEPT_IRI])
    await waitFor(() => {
      expect(screen.getByText(/failed to load graph/i)).toBeInTheDocument()
    })
  })

  it('reloads graph when entityIris changes', async () => {
    const { rerender } = renderPanel([CONCEPT_IRI])
    await waitFor(() => expect(screen.getByTestId('graph-canvas')).toBeInTheDocument())

    rerender(
      <EntityGraphPanel ontologyId={ONTOLOGY_ID} entityIris={[CONCEPT_IRI, ANIMAL_IRI]} onRemoveIri={vi.fn()} />,
    )
    await waitFor(() => {
      expect(screen.getByTestId('graph-canvas')).toBeInTheDocument()
    })
  })

  it('does not include blank-node entities in graph elements', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', () =>
        HttpResponse.json({
          nodes: [
            { iri: 'https://test.example.org/onto#Person', label: 'Person', kind: 'concept' },
            { iri: '_:b1', label: '_:b1', kind: 'individual' },
          ],
          edges: [],
        }),
      ),
    )

    renderPanel([CONCEPT_IRI])
    await waitFor(() => expect(screen.getByTestId('graph-canvas')).toBeInTheDocument())

    // desired behavior: blank-node visual artifacts must be excluded
    expect(screen.getByTestId('graph-canvas').getAttribute('data-elements')).toBe('1')
  })

  it('uses compact labels instead of raw IRI strings for node labels', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', () =>
        HttpResponse.json({
          nodes: [
            {
              iri: 'https://test.example.org/onto#VeryLongEntity',
              label: 'https://test.example.org/onto#VeryLongEntity',
              kind: 'concept',
            },
          ],
          edges: [],
        }),
      ),
    )

    renderPanel([CONCEPT_IRI])
    await waitFor(() => expect(screen.getByTestId('graph-canvas')).toBeInTheDocument())

    const labels = screen.getByTestId('graph-canvas').getAttribute('data-labels') ?? ''
    // desired behavior: raw full IRI should not be used as display label
    expect(labels).not.toContain('https://test.example.org/onto#VeryLongEntity')
    expect(labels).toContain('VeryLongEntity')
  })

  it('excludes OWL restriction edges from graph rendering', async () => {
    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', () =>
        HttpResponse.json({
          nodes: [
            { iri: 'https://test.example.org/onto#Person', label: 'Person', kind: 'concept' },
            { iri: 'https://test.example.org/onto#Department', label: 'Department', kind: 'concept' },
          ],
          edges: [
            {
              source: 'https://test.example.org/onto#Person',
              target: 'https://test.example.org/onto#Department',
              propertyIri: 'http://www.w3.org/2002/07/owl#someValuesFrom',
              propertyLabel: 'someValuesFrom',
            },
          ],
        }),
      ),
    )

    renderPanel([CONCEPT_IRI])
    await waitFor(() => expect(screen.getByTestId('graph-canvas')).toBeInTheDocument())

    // only two concept nodes should remain; restriction edge must be hidden
    expect(screen.getByTestId('graph-canvas').getAttribute('data-elements')).toBe('2')
  })

  it('handles large subgraph payload without including filtered noise', async () => {
    const conceptNodes = Array.from({ length: 400 }).map((_, i) => ({
      iri: `https://test.example.org/onto#C${i}`,
      label: `https://test.example.org/onto#C${i}`,
      kind: 'concept',
    }))
    const blankNodes = Array.from({ length: 100 }).map((_, i) => ({
      iri: `_:b${i}`,
      label: `_:b${i}`,
      kind: 'individual',
    }))
    const restrictionEdges = Array.from({ length: 100 }).map((_, i) => ({
      source: `https://test.example.org/onto#C${i}`,
      target: `https://test.example.org/onto#C${i + 1}`,
      propertyIri: 'http://www.w3.org/2002/07/owl#someValuesFrom',
      propertyLabel: 'someValuesFrom',
    }))
    const validEdges = Array.from({ length: 200 }).map((_, i) => ({
      source: `https://test.example.org/onto#C${i}`,
      target: `https://test.example.org/onto#C${i + 1}`,
      propertyIri: 'SUBCLASS_OF',
      propertyLabel: 'SUBCLASS_OF',
    }))

    server.use(
      http.post('/api/v1/ontologies/:id/subgraph', () =>
        HttpResponse.json({
          nodes: [...conceptNodes, ...blankNodes],
          edges: [...validEdges, ...restrictionEdges],
        }),
      ),
    )

    renderPanel([CONCEPT_IRI])
    await waitFor(() => expect(screen.getByTestId('graph-canvas')).toBeInTheDocument())

    // 400 concept nodes + 200 valid edges; bnodes/restriction edges are filtered out.
    expect(screen.getByTestId('graph-canvas').getAttribute('data-elements')).toBe('600')
  })
})
