import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Pagination from '../Pagination'

describe('Pagination', () => {
  it('renders page info', () => {
    render(<Pagination page={1} pageSize={20} total={45} onPageChange={vi.fn()} />)
    expect(screen.getByText(/1–20/)).toBeInTheDocument()
    expect(screen.getByText(/45/)).toBeInTheDocument()
  })

  it('returns null when total=0', () => {
    const { container } = render(
      <Pagination page={1} pageSize={20} total={0} onPageChange={vi.fn()} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('prev button disabled on first page', () => {
    render(<Pagination page={1} pageSize={20} total={50} onPageChange={vi.fn()} />)
    expect(screen.getByTitle('Previous page')).toBeDisabled()
  })

  it('next button disabled on last page', () => {
    render(<Pagination page={3} pageSize={20} total={50} onPageChange={vi.fn()} />)
    expect(screen.getByTitle('Next page')).toBeDisabled()
  })

  it('calls onPageChange with next page', () => {
    const onPageChange = vi.fn()
    render(<Pagination page={1} pageSize={20} total={50} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByTitle('Next page'))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it('calls onPageChange with prev page', () => {
    const onPageChange = vi.fn()
    render(<Pagination page={3} pageSize={20} total={100} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByTitle('Previous page'))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })
})
