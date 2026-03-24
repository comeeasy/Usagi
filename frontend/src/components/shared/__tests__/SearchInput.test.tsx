import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import SearchInput from '../SearchInput'

describe('SearchInput', () => {
  it('renders with placeholder', () => {
    render(<SearchInput placeholder="Search here..." />)
    expect(screen.getByPlaceholderText('Search here...')).toBeInTheDocument()
  })

  it('shows initial value', () => {
    render(<SearchInput value="initial" />)
    expect(screen.getByDisplayValue('initial')).toBeInTheDocument()
  })

  it('calls onChange after debounce', async () => {
    vi.useFakeTimers()
    const onChange = vi.fn()
    render(<SearchInput onChange={onChange} debounceMs={300} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hello' } })
    expect(onChange).not.toHaveBeenCalled()
    await act(async () => { vi.advanceTimersByTime(300) })
    expect(onChange).toHaveBeenCalledWith('hello')
    vi.useRealTimers()
  })

  it('clear button resets value and calls onChange immediately', () => {
    const onChange = vi.fn()
    render(<SearchInput value="typed" onChange={onChange} />)
    const clearBtn = screen.getByRole('button')
    fireEvent.click(clearBtn)
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('clear button not shown when empty', () => {
    render(<SearchInput value="" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
