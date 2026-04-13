/**
 * SchemaRelationPicker — 스키마에서 Object Property 선택 드롭다운
 */
import { useRef, useState, useEffect } from 'react'
import { Plus, Check, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listObjectProperties } from '@/api/relations'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'

function shortLabel(iri: string, label?: string): string {
  if (label) return label
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}


interface SchemaRelationPickerProps {
  ontologyId: string
  dataset?: string
  selectedIris: string[]
  onAdd: (iri: string) => void
  onRemove: (iri: string) => void
}

export default function SchemaRelationPicker({
  ontologyId,
  dataset,
  selectedIris,
  onAdd,
  onRemove,
}: SchemaRelationPickerProps) {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const { selectedGraphIris } = useNamedGraphs()

  const propsQuery = useQuery({
    queryKey: ['object-properties', ontologyId, dataset, 'picker', selectedGraphIris],
    queryFn: () => listObjectProperties(ontologyId, { pageSize: 200, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId && open,
    staleTime: 30_000,
  })

  // 바깥 클릭 시 닫기
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const q = filter.toLowerCase()
  const properties = (propsQuery.data?.items ?? []).filter(
    (p) => !q || (p.label ?? '').toLowerCase().includes(q) || p.iri.toLowerCase().includes(q),
  )

  const selectedSet = new Set(selectedIris)

  const toggle = (iri: string) => {
    if (selectedSet.has(iri)) onRemove(iri)
    else onAdd(iri)
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 px-2 py-1 rounded border text-xs hover:opacity-80 transition-opacity"
        style={{
          backgroundColor: 'var(--color-bg-elevated)',
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-secondary)',
        }}
      >
        <Plus size={11} />
        Add from Schema
      </button>

      {open && (
        <div
          className="absolute left-0 top-full mt-1 z-50 w-72 rounded border shadow-lg flex flex-col"
          style={{
            backgroundColor: 'var(--color-bg-surface)',
            borderColor: 'var(--color-border)',
            maxHeight: '280px',
          }}
        >
          {/* Filter input */}
          <div
            className="flex items-center gap-1.5 px-2 py-1.5 border-b"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <Search size={11} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
            <input
              autoFocus
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="filter…"
              className="flex-1 bg-transparent text-xs outline-none"
              style={{ color: 'var(--color-text-primary)' }}
            />
          </div>

          <div className="overflow-y-auto flex-1">
            {properties.map((p) => {
              const selected = selectedSet.has(p.iri)
              const domainShort = p.domain[0] ? shortLabel(p.domain[0]) : '?'
              const rangeShort  = p.range[0]  ? shortLabel(p.range[0] as string)  : '?'
              const hint = `${domainShort} → ${rangeShort}`

              return (
                <button
                  key={p.iri}
                  type="button"
                  onClick={() => toggle(p.iri)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-left hover:opacity-80 transition-opacity"
                  style={{
                    backgroundColor: selected ? 'color-mix(in srgb, var(--color-primary) 10%, transparent)' : undefined,
                  }}
                >
                  <span
                    className="w-3.5 h-3.5 flex-shrink-0 flex items-center justify-center rounded border"
                    style={{
                      borderColor: selected ? 'var(--color-primary)' : 'var(--color-border)',
                      backgroundColor: selected ? 'var(--color-primary)' : undefined,
                    }}
                  >
                    {selected && <Check size={9} color="#fff" />}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="text-xs block truncate" style={{ color: 'var(--color-text-primary)' }}>
                      {shortLabel(p.iri, p.label)}
                    </span>
                    <span className="text-xs block truncate" style={{ color: 'var(--color-text-muted)' }}>
                      {hint}
                    </span>
                  </span>
                </button>
              )
            })}

            {properties.length === 0 && (
              <p className="px-2 py-3 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                {propsQuery.isLoading ? 'Loading…' : 'No properties found'}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
