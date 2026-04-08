/**
 * SchemaLeftPanel — Schema 탭 좌측 패널
 *
 * 두 섹션:
 *   ▼ Concepts  [Tree|Flat] [+ New Concept]
 *   ▼ Properties  [All|Object|Data] [+ New Property]
 *      각 property 항목 아래 "domain → range" 인라인 표시
 */
import { useState } from 'react'
import { List, GitBranch, Plus, ChevronDown, ChevronRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listConcepts } from '@/api/entities'
import { listObjectProperties, listDataProperties } from '@/api/relations'
import ConceptTreeView from '@/components/entities/ConceptTreeView'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import type { ObjectProperty, DataProperty } from '@/types/property'

type PropertyFilter = 'all' | 'object' | 'data'
type ConceptViewMode = 'flat' | 'tree'

const PAGE_SIZE = 50

function localName(iri: string): string {
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}

type TaggedObjectProp = ObjectProperty & { _kind: 'object' }
type TaggedDataProp = DataProperty & { _kind: 'data' }
type TaggedProp = TaggedObjectProp | TaggedDataProp

interface Props {
  ontologyId: string
  dataset: string
  selectedIri: string | null
  onSelectConcept: (iri: string) => void
  onSelectProperty: (iri: string, kind: 'object' | 'data', property: ObjectProperty | DataProperty) => void
  conceptViewMode: ConceptViewMode
  onConceptViewModeChange: (m: ConceptViewMode) => void
  propertyFilter: PropertyFilter
  onPropertyFilterChange: (f: PropertyFilter) => void
  onNewConcept: () => void
  onNewProperty: () => void
}

export default function SchemaLeftPanel({
  ontologyId,
  dataset,
  selectedIri,
  onSelectConcept,
  onSelectProperty,
  conceptViewMode,
  onConceptViewModeChange,
  propertyFilter,
  onPropertyFilterChange,
  onNewConcept,
  onNewProperty,
}: Props) {
  const [conceptsOpen, setConceptsOpen] = useState(true)
  const [propertiesOpen, setPropertiesOpen] = useState(true)
  const { selectedGraphIris } = useNamedGraphs()

  // ── Concept queries (flat mode만) ──────────────────────────────
  const conceptsQuery = useQuery({
    queryKey: ['concepts', ontologyId, dataset, 1, selectedGraphIris],
    queryFn: () => listConcepts(ontologyId, { page: 1, pageSize: PAGE_SIZE, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId && conceptViewMode === 'flat',
  })

  // ── Property queries ───────────────────────────────────────────
  const objectQuery = useQuery({
    queryKey: ['object-properties', ontologyId, dataset, 1, selectedGraphIris],
    queryFn: () => listObjectProperties(ontologyId, { page: 1, pageSize: PAGE_SIZE, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId && propertyFilter !== 'data',
  })

  const dataQuery = useQuery({
    queryKey: ['data-properties', ontologyId, dataset, 1, selectedGraphIris],
    queryFn: () => listDataProperties(ontologyId, { page: 1, pageSize: PAGE_SIZE, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId && propertyFilter !== 'object',
  })

  const objectProps: TaggedObjectProp[] = (propertyFilter !== 'data' ? objectQuery.data?.items ?? [] : [])
    .map((p) => ({ ...p, _kind: 'object' as const }))
  const dataProps: TaggedDataProp[] = (propertyFilter !== 'object' ? dataQuery.data?.items ?? [] : [])
    .map((p) => ({ ...p, _kind: 'data' as const }))
  const allProps: TaggedProp[] = [...objectProps, ...dataProps]

  const propLoading =
    (propertyFilter !== 'data' && objectQuery.isLoading) ||
    (propertyFilter !== 'object' && dataQuery.isLoading)

  const propTotal =
    propertyFilter === 'object'
      ? (objectQuery.data?.total ?? 0)
      : propertyFilter === 'data'
        ? (dataQuery.data?.total ?? 0)
        : (objectQuery.data?.total ?? 0) + (dataQuery.data?.total ?? 0)

  return (
    <div
      className="flex flex-col h-full overflow-hidden border-r"
      style={{ borderColor: 'var(--color-border)' }}
    >
      <div className="flex-1 overflow-y-auto">

        {/* ══ Concepts Section ══════════════════════════════════ */}
        <div data-testid="schema-concepts-section">
          {/* Header */}
          <div
            className="flex items-center gap-1 px-3 py-2 border-b sticky top-0 z-10"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              borderColor: 'var(--color-border)',
            }}
          >
            <button
              onClick={() => setConceptsOpen((v) => !v)}
              className="p-0.5 hover:opacity-60"
              style={{ color: 'var(--color-text-muted)' }}
            >
              {conceptsOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </button>

            <span className="text-xs font-semibold flex-1" style={{ color: 'var(--color-text-secondary)' }}>
              Concepts
              {conceptsQuery.data && conceptViewMode === 'flat' && (
                <span className="ml-1 font-normal" style={{ color: 'var(--color-text-muted)' }}>
                  ({conceptsQuery.data.total})
                </span>
              )}
            </span>

            {/* Tree / Flat toggle */}
            <div
              className="flex border rounded overflow-hidden mr-1"
              style={{ borderColor: 'var(--color-border)' }}
            >
              {(['flat', 'tree'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => onConceptViewModeChange(mode)}
                  title={mode === 'flat' ? 'Flat list' : 'Tree view'}
                  className="px-1.5 py-1 flex items-center transition-colors"
                  style={{
                    backgroundColor: conceptViewMode === mode ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                    color: conceptViewMode === mode ? '#fff' : 'var(--color-text-secondary)',
                  }}
                >
                  {mode === 'flat' ? <List size={11} /> : <GitBranch size={11} />}
                </button>
              ))}
            </div>

            <button
              onClick={onNewConcept}
              className="flex items-center gap-0.5 px-2 py-1 rounded text-xs font-medium hover:opacity-80"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              <Plus size={11} />
              New Concept
            </button>
          </div>

          {/* Concept list */}
          {conceptsOpen && (
            conceptViewMode === 'tree' ? (
              <div style={{ minHeight: '160px' }}>
                <ConceptTreeView
                  ontologyId={ontologyId}
                  dataset={dataset}
                  selectedIri={selectedIri}
                  onSelect={onSelectConcept}
                />
              </div>
            ) : (
              <div>
                {conceptsQuery.isLoading && (
                  <div className="flex justify-center py-6">
                    <LoadingSpinner size="sm" />
                  </div>
                )}
                {!conceptsQuery.isLoading && (conceptsQuery.data?.items ?? []).length === 0 && (
                  <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                    No concepts
                  </div>
                )}
                {(conceptsQuery.data?.items ?? []).map((concept) => (
                  <div
                    key={concept.iri}
                    onClick={() => onSelectConcept(concept.iri)}
                    className="px-3 py-2 cursor-pointer border-b text-sm transition-colors"
                    style={{
                      borderColor: 'var(--color-border)',
                      backgroundColor:
                        selectedIri === concept.iri ? 'var(--color-bg-elevated)' : 'transparent',
                      color:
                        selectedIri === concept.iri
                          ? 'var(--color-primary)'
                          : 'var(--color-text-primary)',
                    }}
                    onMouseEnter={(e) => {
                      if (selectedIri !== concept.iri)
                        e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)'
                    }}
                    onMouseLeave={(e) => {
                      if (selectedIri !== concept.iri)
                        e.currentTarget.style.backgroundColor = 'transparent'
                    }}
                  >
                    {concept.label || localName(concept.iri)}
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* ══ Properties Section ════════════════════════════════ */}
        <div data-testid="schema-properties-section" className="border-t" style={{ borderColor: 'var(--color-border)' }}>
          {/* Header */}
          <div
            className="flex items-center gap-1 px-3 py-2 border-b sticky top-0 z-10"
            style={{
              backgroundColor: 'var(--color-bg-surface)',
              borderColor: 'var(--color-border)',
            }}
          >
            <button
              onClick={() => setPropertiesOpen((v) => !v)}
              className="p-0.5 hover:opacity-60"
              style={{ color: 'var(--color-text-muted)' }}
            >
              {propertiesOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </button>

            <span className="text-xs font-semibold flex-1" style={{ color: 'var(--color-text-secondary)' }}>
              Properties
              {propTotal > 0 && (
                <span className="ml-1 font-normal" style={{ color: 'var(--color-text-muted)' }}>
                  ({propTotal})
                </span>
              )}
            </span>

            {/* All / Object / Data filter */}
            <div
              className="flex border rounded overflow-hidden mr-1"
              style={{ borderColor: 'var(--color-border)' }}
            >
              {(['all', 'object', 'data'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => onPropertyFilterChange(f)}
                  className="px-2 py-1 text-xs transition-colors"
                  style={{
                    backgroundColor: propertyFilter === f ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                    color: propertyFilter === f ? '#fff' : 'var(--color-text-secondary)',
                  }}
                >
                  {f === 'all' ? 'All' : f === 'object' ? 'Object' : 'Data'}
                </button>
              ))}
            </div>

            <button
              onClick={onNewProperty}
              className="flex items-center gap-0.5 px-2 py-1 rounded text-xs font-medium hover:opacity-80"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              <Plus size={11} />
              New Property
            </button>
          </div>

          {/* Property list */}
          {propertiesOpen && (
            <div>
              {propLoading && (
                <div className="flex justify-center py-6">
                  <LoadingSpinner size="sm" />
                </div>
              )}
              {!propLoading && allProps.length === 0 && (
                <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                  No properties
                </div>
              )}
              {allProps.map((prop) => {
                const isObject = prop._kind === 'object'
                const domainLabel = prop.domain[0] ? localName(prop.domain[0]) : '—'
                const rangeLabel = prop.range[0] ? localName(prop.range[0] as string) : '—'
                const isSelected = selectedIri === prop.iri

                return (
                  <div
                    key={prop.iri}
                    onClick={() => onSelectProperty(prop.iri, prop._kind, prop)}
                    className="px-3 py-2 cursor-pointer border-b transition-colors"
                    style={{
                      borderColor: 'var(--color-border)',
                      backgroundColor: isSelected ? 'var(--color-bg-elevated)' : 'transparent',
                    }}
                    onMouseEnter={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)'
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent'
                    }}
                  >
                    {/* Label row */}
                    <div className="flex items-center gap-1.5">
                      <span
                        className="text-xs font-mono w-3 flex-shrink-0"
                        style={{ color: isObject ? '#A371F7' : 'var(--color-warning)' }}
                      >
                        {isObject ? '≈' : '—'}
                      </span>
                      <span
                        className="text-sm font-medium truncate"
                        style={{
                          color: isSelected ? 'var(--color-primary)' : 'var(--color-text-primary)',
                        }}
                      >
                        {prop.label || localName(prop.iri)}
                      </span>
                    </div>
                    {/* domain → range */}
                    <div className="ml-4 mt-0.5 text-xs flex items-center gap-1" style={{ color: 'var(--color-text-muted)' }}>
                      <span>{domainLabel}</span>
                      <span style={{ color: 'var(--color-text-secondary)' }}>→</span>
                      <span>{rangeLabel}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
