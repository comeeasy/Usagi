/**
 * Tests for ConceptForm — IRI/label/comment + advanced OWL fields
 * (super_classes, equivalent_classes, disjoint_with, restrictions)
 */
import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConceptForm from '../ConceptForm'
import { renderWithProviders } from '@/tests/utils'

// IRISearchInput uses useEntitySearch/useSearchRelations (react-query) + useParams
// Mock them so tests don't need a real API
vi.mock('@/hooks/useEntitySearch', () => ({
  useEntitySearch: () => ({ data: [], isFetching: false }),
  useSearchRelations: () => ({ data: [], isFetching: false }),
}))

const SAMPLE_IRI = 'https://x.org#MyClass'

function renderForm(props: React.ComponentProps<typeof ConceptForm> = {}) {
  return renderWithProviders(<ConceptForm {...props} />, {
    initialEntries: ['/ontologies/test-onto/concepts'],
    path: '/ontologies/:ontologyId/concepts',
  })
}

/** Fill the main IRI field so the form can be submitted (required in create mode). */
async function fillIRI(iri = SAMPLE_IRI) {
  const iriInput = screen.getByPlaceholderText(/https:\/\/example\.org\/MyClass/i)
  await userEvent.type(iriInput, iri)
}

describe('ConceptForm — basic fields', () => {
  it('renders IRI, Label, Comment inputs in create mode', () => {
    renderForm()
    expect(screen.getByPlaceholderText(/https:\/\/example\.org\/MyClass/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Human readable label/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Description of this class/i)).toBeInTheDocument()
  })

  it('shows Create button in create mode, Save in edit mode', () => {
    const { rerender } = renderWithProviders(<ConceptForm mode="create" />, {
      initialEntries: ['/ontologies/test-onto/concepts'],
      path: '/ontologies/:ontologyId/concepts',
    })
    expect(screen.getByRole('button', { name: /Create/i })).toBeInTheDocument()

    rerender(<ConceptForm mode="edit" />)
    expect(screen.getByRole('button', { name: /Save/i })).toBeInTheDocument()
  })

  it('disables IRI input in edit mode', () => {
    renderForm({ mode: 'edit', initialValues: { iri: 'https://x.org#C' } })
    const iriInput = screen.getByDisplayValue('https://x.org#C')
    expect(iriInput).toBeDisabled()
  })

  it('calls onSubmit with form values on submit', async () => {
    const onSubmit = vi.fn()
    renderForm({ onSubmit })
    await userEvent.type(screen.getByPlaceholderText(/https:\/\/example\.org\/MyClass/i), SAMPLE_IRI)
    await userEvent.type(screen.getByPlaceholderText(/Human readable label/i), 'My Class')
    fireEvent.click(screen.getByRole('button', { name: /Create/i }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ iri: SAMPLE_IRI, label: 'My Class' }),
    )
  })

  it('calls onCancel when Cancel button is clicked', async () => {
    const onCancel = vi.fn()
    renderForm({ onCancel })
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(onCancel).toHaveBeenCalled()
  })

  it('populates initialValues into fields', () => {
    renderForm({
      mode: 'edit',
      initialValues: { iri: 'https://x.org#C', label: 'ClassC', comment: 'desc' },
    })
    expect(screen.getByDisplayValue('ClassC')).toBeInTheDocument()
    expect(screen.getByDisplayValue('desc')).toBeInTheDocument()
  })
})

describe('ConceptForm — IRIListSearchInput (superClasses / equivalentClasses / disjointWith)', () => {
  it('adds a super class IRI via Enter key and includes it in submission', async () => {
    const onSubmit = vi.fn()
    renderForm({ onSubmit })
    await fillIRI()

    // IRIListSearchInput for Parent Classes uses placeholder "Search or enter class IRI…"
    const parentInputs = screen.getAllByPlaceholderText(/Search or enter class IRI/i)
    await userEvent.type(parentInputs[0], 'https://x.org#Animal{Enter}')

    // tag should appear as a chip
    expect(screen.getByText('https://x.org#Animal')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Create/i }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ superClasses: ['https://x.org#Animal'] }),
    )
  })

  it('removes a tag using its × button', async () => {
    renderForm({ initialValues: { superClasses: ['https://x.org#Base'] } })
    expect(screen.getByText('https://x.org#Base')).toBeInTheDocument()

    // the × button is the sibling of the text span inside the chip wrapper
    const tag = screen.getByText('https://x.org#Base').parentElement!
    const removeBtn = tag.querySelector('button')!
    fireEvent.click(removeBtn)

    await waitFor(() => {
      expect(screen.queryByText('https://x.org#Base')).not.toBeInTheDocument()
    })
  })

  it('submits equivalentClasses when added', async () => {
    const onSubmit = vi.fn()
    renderForm({ onSubmit })
    await fillIRI()

    const inputs = screen.getAllByPlaceholderText(/Search or enter class IRI/i)
    // Second IRIListSearchInput is equivalentClasses
    await userEvent.type(inputs[1], 'https://x.org#EqClass{Enter}')

    fireEvent.click(screen.getByRole('button', { name: /Create/i }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ equivalentClasses: ['https://x.org#EqClass'] }),
    )
  })

  it('submits disjointWith when added', async () => {
    const onSubmit = vi.fn()
    renderForm({ onSubmit })
    await fillIRI()

    const inputs = screen.getAllByPlaceholderText(/Search or enter class IRI/i)
    // Third IRIListSearchInput is disjointWith
    await userEvent.type(inputs[2], 'https://x.org#Other{Enter}')

    fireEvent.click(screen.getByRole('button', { name: /Create/i }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ disjointWith: ['https://x.org#Other'] }),
    )
  })
})

describe('ConceptForm — RestrictionEditor', () => {
  it('renders restriction type selector with someValuesFrom default', () => {
    renderForm()
    const select = screen.getByRole('combobox')
    expect((select as HTMLSelectElement).value).toBe('someValuesFrom')
  })

  it('adds a someValuesFrom restriction via the + button', async () => {
    const onSubmit = vi.fn()
    renderForm({ onSubmit })
    await fillIRI()

    await userEvent.type(screen.getByPlaceholderText(/Search or enter property IRI/i), 'https://x.org#worksIn{Enter}')
    await userEvent.type(screen.getByPlaceholderText(/Filler IRI or value/i), 'https://x.org#Dept{Enter}')

    // add button (+) in the restriction panel
    const addPanel = screen.getByText('Add restriction').closest('div')!.parentElement!
    const addBtn = addPanel.querySelector('button[type="button"]')!
    fireEvent.click(addBtn)

    fireEvent.click(screen.getByRole('button', { name: /Create/i }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        restrictions: [
          expect.objectContaining({
            type: 'someValuesFrom',
            property_iri: 'https://x.org#worksIn',
            value: 'https://x.org#Dept',
          }),
        ],
      }),
    )
  })

  it('shows cardinality input only for cardinality restriction types', async () => {
    renderForm()
    const select = screen.getByRole('combobox')

    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()

    await userEvent.selectOptions(select, 'minCardinality')
    expect(screen.getByRole('spinbutton')).toBeInTheDocument()

    await userEvent.selectOptions(select, 'someValuesFrom')
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument()
  })

  it('includes cardinality in submitted restriction', async () => {
    const onSubmit = vi.fn()
    renderForm({ onSubmit })
    await fillIRI()

    const select = screen.getByRole('combobox')
    await userEvent.selectOptions(select, 'minCardinality')

    const cardinalityInput = screen.getByRole('spinbutton')
    await userEvent.clear(cardinalityInput)
    await userEvent.type(cardinalityInput, '2')

    await userEvent.type(screen.getByPlaceholderText(/Search or enter property IRI/i), 'https://x.org#manages{Enter}')

    const addPanel = screen.getByText('Add restriction').closest('div')!.parentElement!
    const addBtn = addPanel.querySelector('button[type="button"]')!
    fireEvent.click(addBtn)

    fireEvent.click(screen.getByRole('button', { name: /Create/i }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        restrictions: [
          expect.objectContaining({ type: 'minCardinality', cardinality: 2 }),
        ],
      }),
    )
  })

  it('removes a restriction by clicking its × button', async () => {
    renderForm({
      initialValues: {
        restrictions: [{ property_iri: 'https://x.org#p', type: 'someValuesFrom', value: 'https://x.org#C' }],
      },
    })
    // restriction row is visible
    const typeLabel = screen.getByText('someValuesFrom')
    expect(typeLabel).toBeInTheDocument()

    // the × button is in the restriction row
    const row = typeLabel.closest('div[style]')!
    const removeBtn = row.querySelector('button')!
    fireEvent.click(removeBtn)

    await waitFor(() => {
      expect(screen.queryByText('someValuesFrom')).not.toBeInTheDocument()
    })
  })
})
