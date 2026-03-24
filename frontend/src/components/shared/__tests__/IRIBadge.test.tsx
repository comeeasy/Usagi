import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import IRIBadge from '../IRIBadge'

describe('IRIBadge', () => {
  it('renders short form for known prefixes', () => {
    render(<IRIBadge iri="http://www.w3.org/2002/07/owl#Class" />)
    expect(screen.getByText('owl:Class')).toBeInTheDocument()
  })

  it('renders fragment shorthand for unknown IRI', () => {
    render(<IRIBadge iri="https://example.org/onto#Person" />)
    expect(screen.getByText('...#Person')).toBeInTheDocument()
  })

  it('shows full IRI in title attribute', () => {
    render(<IRIBadge iri="https://example.org/onto#Person" />)
    expect(screen.getByTitle('https://example.org/onto#Person')).toBeInTheDocument()
  })

  it('calls onClick with full IRI when clicked', () => {
    const onClick = vi.fn()
    render(<IRIBadge iri="https://example.org/onto#Person" onClick={onClick} />)
    fireEvent.click(screen.getByTitle('https://example.org/onto#Person'))
    expect(onClick).toHaveBeenCalledWith('https://example.org/onto#Person')
  })

  it('shows copy button when showCopy=true', () => {
    render(<IRIBadge iri="https://example.org/onto#X" showCopy />)
    expect(screen.getByTitle('Copy IRI')).toBeInTheDocument()
  })

  it('does not show copy button by default', () => {
    render(<IRIBadge iri="https://example.org/onto#X" />)
    expect(screen.queryByTitle('Copy IRI')).not.toBeInTheDocument()
  })
})
