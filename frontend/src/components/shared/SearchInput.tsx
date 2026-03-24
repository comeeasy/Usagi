import { useState, useEffect, useRef } from 'react'
import { Search, X } from 'lucide-react'

interface SearchInputProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  debounceMs?: number
  className?: string
}

export default function SearchInput({
  value = '',
  onChange,
  placeholder = 'Search...',
  debounceMs = 300,
  className = '',
}: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setLocalValue(value)
  }, [value])

  const handleChange = (newValue: string) => {
    setLocalValue(newValue)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      onChange?.(newValue)
    }, debounceMs)
  }

  const handleClear = () => {
    setLocalValue('')
    onChange?.('')
  }

  return (
    <div className={`relative flex items-center ${className}`}>
      <Search
        size={14}
        className="absolute left-2.5 pointer-events-none"
        style={{ color: 'var(--color-text-muted)' }}
      />
      <input
        type="text"
        value={localValue}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-8 pr-8 py-1.5 rounded border text-sm focus:outline-none"
        style={{
          backgroundColor: 'var(--color-bg-elevated)',
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-primary)',
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = 'var(--color-primary)'
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = 'var(--color-border)'
        }}
      />
      {localValue && (
        <button
          className="absolute right-2 hover:opacity-80"
          onClick={handleClear}
          style={{ color: 'var(--color-text-muted)' }}
        >
          <X size={14} />
        </button>
      )}
    </div>
  )
}
