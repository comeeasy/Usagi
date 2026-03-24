import { useState } from 'react'
import SearchInput from '@/components/shared/SearchInput'

interface RelationSearchBarProps {
  onSearch?: (query: string, domainIri?: string, rangeIri?: string) => void
}

export default function RelationSearchBar({ onSearch }: RelationSearchBarProps) {
  const [query, setQuery] = useState('')
  const [domain, setDomain] = useState('')
  const [range, setRange] = useState('')

  const handleChange = (q: string, d: string, r: string) => {
    onSearch?.(q, d || undefined, r || undefined)
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  return (
    <div className="flex gap-2 items-center flex-wrap">
      <SearchInput
        value={query}
        onChange={(v) => { setQuery(v); handleChange(v, domain, range) }}
        placeholder="Search relations..."
        className="flex-1 min-w-48"
      />
      <input
        type="text"
        value={domain}
        onChange={(e) => { setDomain(e.target.value); handleChange(query, e.target.value, range) }}
        placeholder="Domain IRI filter"
        className="px-2 py-1.5 rounded border text-xs font-mono focus:outline-none"
        style={{ ...inputStyle, width: 180 }}
      />
      <input
        type="text"
        value={range}
        onChange={(e) => { setRange(e.target.value); handleChange(query, domain, e.target.value) }}
        placeholder="Range IRI filter"
        className="px-2 py-1.5 rounded border text-xs font-mono focus:outline-none"
        style={{ ...inputStyle, width: 180 }}
      />
    </div>
  )
}
