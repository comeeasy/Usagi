/**
 * Tests for MergePage — 3-step merge flow (select → preview → done)
 */
import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../tests/mocks/server'
import { renderWithProviders } from '../../../tests/utils'
import MergePage from '../MergePage'

const ROUTE_PATH = '/:ontologyId/merge'
const INITIAL_ENTRY = '/test-ont-uuid/merge'

const mockSourceOntology = {
  id: 'source-ont-uuid',
  name: 'Source Ontology',
  description: '',
  base_iri: 'https://source.example.org/onto',
  version: '1.0.0',
  created_at: '2026-03-25T00:00:00Z',
  updated_at: '2026-03-25T00:00:00Z',
  stats: {},
}

function renderMergePage() {
  return renderWithProviders(<MergePage />, {
    initialEntries: [INITIAL_ENTRY],
    path: ROUTE_PATH,
  })
}

/** Set up MSW to return [mockSourceOntology] for the ontologies list. */
function useSourceOntologyList() {
  server.use(
    http.get('/api/v1/ontologies', () =>
      HttpResponse.json({ items: [mockSourceOntology], total: 1, page: 1, page_size: 20 }),
    ),
  )
}

/** Wait for source options to load, then select the source ontology and click Preview. */
async function selectAndPreview() {
  await waitFor(() =>
    expect(screen.getByRole('option', { name: /Source Ontology/i })).toBeInTheDocument(),
  )
  await userEvent.selectOptions(screen.getByRole('combobox'), 'source-ont-uuid')
  await userEvent.click(screen.getByRole('button', { name: /Preview & Resolve/i }))
}

/** Go to preview step with no-conflict mock. */
async function goToPreviewNoConflicts(autoMergeableCount = 5) {
  useSourceOntologyList()
  server.use(
    http.post('/api/v1/ontologies/:id/merge/preview', () =>
      HttpResponse.json({ conflicts: [], conflict_count: 0, auto_mergeable_count: autoMergeableCount }),
    ),
  )
  renderMergePage()
  await selectAndPreview()
  await waitFor(() => expect(screen.getByText(/No conflicts detected/i)).toBeInTheDocument())
}

describe('MergePage — step: select', () => {
  it('renders the Merge Ontologies heading', () => {
    renderMergePage()
    expect(screen.getByText('Merge Ontologies')).toBeInTheDocument()
  })

  it('shows a source ontology dropdown', () => {
    renderMergePage()
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('Preview button is disabled when no source selected', () => {
    renderMergePage()
    expect(screen.getByRole('button', { name: /Preview & Resolve/i })).toBeDisabled()
  })

  it('lists other ontologies in the source dropdown', async () => {
    useSourceOntologyList()
    renderMergePage()
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Source Ontology/i })).toBeInTheDocument()
    })
  })
})

describe('MergePage — step: preview (no conflicts)', () => {
  it('transitions to preview step after clicking Preview & Resolve', async () => {
    await goToPreviewNoConflicts()
    expect(screen.getByText(/No conflicts detected/i)).toBeInTheDocument()
  })

  it('shows auto-merge count in the preview step', async () => {
    await goToPreviewNoConflicts(7)
    // The auto-merge count is displayed as a large number
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('shows a Merge button in the preview step', async () => {
    await goToPreviewNoConflicts()
    expect(screen.getAllByRole('button').some((b) => /^Merge/.test(b.textContent ?? ''))).toBe(true)
  })

  it('Back button resets to the select step', async () => {
    await goToPreviewNoConflicts()
    await userEvent.click(screen.getByRole('button', { name: /Back/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Preview & Resolve/i })).toBeInTheDocument()
    })
  })
})

describe('MergePage — step: preview (with conflicts)', () => {
  const conflict = {
    iri: 'https://shared.example.org#Thing',
    conflict_type: 'label' as const,
    target_value: 'OldLabel',
    source_value: 'NewLabel',
  }

  async function goToConflictPreview() {
    useSourceOntologyList()
    server.use(
      http.post('/api/v1/ontologies/:id/merge/preview', () =>
        HttpResponse.json({ conflicts: [conflict], conflict_count: 1, auto_mergeable_count: 2 }),
      ),
    )
    renderMergePage()
    await selectAndPreview()
    await waitFor(() => expect(screen.getByText('OldLabel')).toBeInTheDocument())
  }

  it('shows conflict items with target and source values', async () => {
    await goToConflictPreview()
    expect(screen.getByText('OldLabel')).toBeInTheDocument()
    expect(screen.getByText('NewLabel')).toBeInTheDocument()
  })

  it('shows resolution choice buttons for each conflict', async () => {
    await goToConflictPreview()
    expect(screen.getByRole('button', { name: /Keep Current/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Use Source/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Keep Both/i })).toBeInTheDocument()
  })
})

describe('MergePage — step: done', () => {
  async function goToDoneStep(tripleCount = 15) {
    useSourceOntologyList()
    server.use(
      http.post('/api/v1/ontologies/:id/merge/preview', () =>
        HttpResponse.json({ conflicts: [], conflict_count: 0, auto_mergeable_count: 3 }),
      ),
      http.post('/api/v1/ontologies/:id/merge', () =>
        HttpResponse.json({ merged: true, triple_count: tripleCount }),
      ),
    )
    renderMergePage()
    await selectAndPreview()
    await waitFor(() => expect(screen.getByText(/No conflicts detected/i)).toBeInTheDocument())

    // Find and click the Merge button (starts with "Merge")
    const mergeBtn = screen.getAllByRole('button').find((b) =>
      /^Merge/.test(b.textContent ?? ''),
    )!
    await userEvent.click(mergeBtn)
    await waitFor(() => expect(screen.getByText('Merge complete')).toBeInTheDocument())
  }

  it('shows Merge complete after successful merge', async () => {
    await goToDoneStep(15)
    expect(screen.getByText('Merge complete')).toBeInTheDocument()
  })

  it('shows triple count in done step', async () => {
    await goToDoneStep(15)
    expect(screen.getByText(/15 triples/i)).toBeInTheDocument()
  })

  it('shows a Merge another button in done step', async () => {
    await goToDoneStep()
    expect(screen.getByRole('button', { name: /Merge another/i })).toBeInTheDocument()
  })

  it('Merge another resets to the select step', async () => {
    await goToDoneStep()
    await userEvent.click(screen.getByRole('button', { name: /Merge another/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Preview & Resolve/i })).toBeInTheDocument()
    })
  })
})
