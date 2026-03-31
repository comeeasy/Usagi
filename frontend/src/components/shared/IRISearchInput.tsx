/**
 * IRISearchInput — 온톨로지 엔티티 검색 드롭다운이 붙은 IRI 입력 컴포넌트
 *
 * - 타이핑하면 existing 엔티티를 검색해 드롭다운 표시
 * - 클릭 시 해당 IRI를 onSelect에 전달
 * - 맨 아래 "New + {query}" 버튼: 입력값 그대로 새 IRI로 사용
 *
 * kind:
 *   'concept'    → owl:Class 검색
 *   'individual' → owl:NamedIndividual 검색
 *   'property'   → ObjectProperty / DataProperty 검색 (searchRelations)
 *   'all'        → 전체 엔티티 검색 (기본)
 */
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Search, Plus } from 'lucide-react'
import { useEntitySearch, useSearchRelations } from '@/hooks/useEntitySearch'
import LoadingSpinner from './LoadingSpinner'

export type IRIKind = 'all' | 'concept' | 'individual' | 'property'

interface IRISearchInputProps {
  value: string
  onChange: (iri: string) => void
  placeholder?: string
  kind?: IRIKind
  disabled?: boolean
  required?: boolean
  className?: string
}

export default function IRISearchInput({
  value,
  onChange,
  placeholder = 'Search or enter IRI…',
  kind = 'all',
  disabled = false,
  required = false,
  className = '',
}: IRISearchInputProps) {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // value prop이 외부에서 바뀌면 동기화 (edit 모드 초기값)
  useEffect(() => { setQuery(value) }, [value])

  const entitySearch = useEntitySearch(
    kind !== 'property' ? ontologyId : undefined,
    query,
    kind === 'concept' ? 'concept' : kind === 'individual' ? 'individual' : 'all',
  )

  const propSearch = useSearchRelations(
    kind === 'property' ? ontologyId : undefined,
    query,
  )

  const results = kind === 'property'
    ? (propSearch.data ?? [])
    : (entitySearch.data ?? [])

  const isFetching = kind === 'property' ? propSearch.isFetching : entitySearch.isFetching

  const handleSelect = (iri: string) => {
    onChange(iri)
    setQuery(iri)
    setOpen(false)
  }

  const handleNewIri = () => {
    const v = query.trim()
    if (v) { onChange(v); setOpen(false) }
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded border text-sm"
        style={inputStyle}
      >
        <Search size={12} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
        <input
          type="text"
          value={query}
          disabled={disabled}
          required={required}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => { if (query) setOpen(true) }}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); results[0] ? handleSelect(results[0].iri) : handleNewIri() }
            if (e.key === 'Escape') setOpen(false)
          }}
          placeholder={placeholder}
          className="flex-1 bg-transparent outline-none font-mono text-xs min-w-0"
          style={{ color: 'var(--color-text-primary)' }}
        />
        {isFetching && <LoadingSpinner size="sm" />}
      </div>

      {open && query.trim().length > 0 && (
        <div
          className="absolute z-50 top-full left-0 right-0 mt-1 rounded-lg border shadow-lg overflow-hidden"
          style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)', maxHeight: '200px', overflowY: 'auto' }}
        >
          {results.slice(0, 10).map((r) => (
            <button
              key={r.iri}
              type="button"
              onMouseDown={() => handleSelect(r.iri)}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:opacity-80 text-xs border-b"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <span
                className="px-1 py-0.5 rounded text-xs flex-shrink-0"
                style={{
                  backgroundColor: 'kind' in r && (r as { kind?: string }).kind === 'individual'
                    ? 'rgba(63,185,80,0.15)' : 'rgba(47,129,247,0.15)',
                  color: 'kind' in r && (r as { kind?: string }).kind === 'individual'
                    ? 'var(--color-success)' : 'var(--color-primary)',
                }}
              >
                {'kind' in r ? (r as { kind?: string }).kind?.[0]?.toUpperCase() ?? '?' : 'P'}
              </span>
              <span className="font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>
                {r.label || r.iri}
              </span>
              <span className="truncate font-mono flex-shrink-0 text-xs" style={{ color: 'var(--color-text-muted)', maxWidth: '40%' }}>
                {r.iri}
              </span>
            </button>
          ))}

          {/* New + 버튼: 항상 맨 아래 */}
          <button
            type="button"
            onMouseDown={handleNewIri}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:opacity-80 text-xs"
            style={{ color: 'var(--color-primary)' }}
          >
            <Plus size={11} />
            <span>New: </span>
            <span className="font-mono truncate" style={{ color: 'var(--color-text-muted)' }}>{query}</span>
          </button>
        </div>
      )}
    </div>
  )
}
