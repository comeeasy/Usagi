import { useState } from 'react'
import SearchInput from '@/components/shared/SearchInput'

interface EntitySearchBarProps {
  onSearch?: (query: string, kind: string, vectorSearch: boolean) => void
}

export default function EntitySearchBar({ onSearch }: EntitySearchBarProps) {
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState('all')
  const [vectorSearch, setVectorSearch] = useState(false)

  const handleQueryChange = (value: string) => {
    setQuery(value)
    onSearch?.(value, kind, vectorSearch)
  }

  const handleKindChange = (value: string) => {
    setKind(value)
    onSearch?.(query, value, vectorSearch)
  }

  const handleVectorToggle = () => {
    const next = !vectorSearch
    setVectorSearch(next)
    onSearch?.(query, kind, next)
  }

  return (
    <div className="flex gap-2 items-center flex-wrap">
      <SearchInput
        value={query}
        onChange={handleQueryChange}
        placeholder="Search entities..."
        className="flex-1 min-w-48"
      />

      <select
        value={kind}
        onChange={(e) => handleKindChange(e.target.value)}
        className="text-sm px-2 py-1.5 rounded border"
        style={{
          backgroundColor: 'var(--color-bg-elevated)',
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-primary)',
        }}
      >
        <option value="all">All types</option>
        <option value="concept">Concepts</option>
        <option value="individual">Individuals</option>
      </select>

      <label className="flex items-center gap-1.5 text-sm cursor-pointer select-none">
        <div
          className={`w-8 h-4 rounded-full transition-colors relative cursor-pointer`}
          style={{
            backgroundColor: vectorSearch ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
          }}
          onClick={handleVectorToggle}
        >
          <div
            className="absolute top-0.5 w-3 h-3 rounded-full transition-transform"
            style={{
              backgroundColor: 'var(--color-text-primary)',
              transform: vectorSearch ? 'translateX(16px)' : 'translateX(1px)',
            }}
          />
        </div>
        <span style={{ color: 'var(--color-text-secondary)' }}>Vector</span>
      </label>
    </div>
  )
}
