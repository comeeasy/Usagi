/**
 * SchemaEntityPicker — 스키마에서 Entity(Concept/Individual) 선택 드롭다운
 */
import { useRef, useState, useEffect } from 'react'
import { Plus, Check, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listConcepts, listIndividuals } from '@/api/entities'

function shortLabel(iri: string, label?: string): string {
  if (label) return label
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}

function shortIri(iri: string): string {
  const h = iri.lastIndexOf('#')
  if (h !== -1) return '…' + iri.slice(h)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? '…' + iri.slice(s) : iri
}

interface SchemaEntityPickerProps {
  ontologyId: string
  dataset?: string
  selectedIris: string[]
  onAdd: (iri: string) => void
  onRemove: (iri: string) => void
}

export default function SchemaEntityPicker({
  ontologyId,
  dataset,
  selectedIris,
  onAdd,
  onRemove,
}: SchemaEntityPickerProps) {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  const conceptsQuery = useQuery({
    queryKey: ['concepts', ontologyId, dataset, 'picker'],
    queryFn: () => listConcepts(ontologyId, { pageSize: 200, dataset }),
    enabled: !!ontologyId && open,
    staleTime: 30_000,
  })

  const individualsQuery = useQuery({
    queryKey: ['individuals', ontologyId, dataset, 'picker'],
    queryFn: () => listIndividuals(ontologyId, { pageSize: 200, dataset }),
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

  const concepts = (conceptsQuery.data?.items ?? []).filter(
    (c) => !q || (c.label ?? '').toLowerCase().includes(q) || c.iri.toLowerCase().includes(q),
  )
  const individuals = (individualsQuery.data?.items ?? []).filter(
    (i) => !q || (i.label ?? '').toLowerCase().includes(q) || i.iri.toLowerCase().includes(q),
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
          className="absolute left-0 top-full mt-1 z-50 w-64 rounded border shadow-lg flex flex-col"
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
            {/* Concepts */}
            {concepts.length > 0 && (
              <>
                <div
                  className="px-2 py-1 text-xs font-semibold sticky top-0"
                  style={{
                    color: 'var(--color-text-muted)',
                    backgroundColor: 'var(--color-bg-surface)',
                  }}
                >
                  Concepts
                </div>
                {concepts.map((c) => {
                  const selected = selectedSet.has(c.iri)
                  return (
                    <button
                      key={c.iri}
                      type="button"
                      onClick={() => toggle(c.iri)}
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
                          {shortLabel(c.iri, c.label)}
                        </span>
                        <span className="text-xs block truncate font-mono" style={{ color: 'var(--color-text-muted)' }}>
                          {shortIri(c.iri)}
                        </span>
                      </span>
                    </button>
                  )
                })}
              </>
            )}

            {/* Individuals */}
            {individuals.length > 0 && (
              <>
                <div
                  className="px-2 py-1 text-xs font-semibold sticky top-0"
                  style={{
                    color: 'var(--color-text-muted)',
                    backgroundColor: 'var(--color-bg-surface)',
                  }}
                >
                  Individuals
                </div>
                {individuals.map((i) => {
                  const selected = selectedSet.has(i.iri)
                  return (
                    <button
                      key={i.iri}
                      type="button"
                      onClick={() => toggle(i.iri)}
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
                          {shortLabel(i.iri, i.label)}
                        </span>
                        <span className="text-xs block truncate font-mono" style={{ color: 'var(--color-text-muted)' }}>
                          {shortIri(i.iri)}
                        </span>
                      </span>
                    </button>
                  )
                })}
              </>
            )}

            {concepts.length === 0 && individuals.length === 0 && (
              <p className="px-2 py-3 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                {conceptsQuery.isLoading || individualsQuery.isLoading ? 'Loading…' : 'No items found'}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
