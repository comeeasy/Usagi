/**
 * SchemaLeftPanel — Schema 탭 좌측 패널
 *
 * 서브탭:
 *   [Concepts] [Properties]
 *
 *   Concepts  탭: ConceptTreeView + New Concept 버튼
 *   Properties 탭: [All|Object|Data] 필터 + property 목록 + New Property 버튼
 */
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listObjectProperties, listDataProperties, } from '@/api/relations'
import { listIndividuals } from '@/api/entities'
import ConceptTreeView from '@/components/entities/ConceptTreeView'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import type { ObjectProperty, DataProperty } from '@/types/property'
import type { Individual } from '@/types/individual'

type PropertyFilter = 'all' | 'object' | 'data'
type ActiveTab = 'concepts' | 'properties' | 'individuals'

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
  onSelectIndividual: (iri: string) => void
  propertyFilter: PropertyFilter
  onPropertyFilterChange: (f: PropertyFilter) => void
  onNewConcept: () => void
  onNewProperty: () => void
  onNewIndividual: () => void
}

export default function SchemaLeftPanel({
  ontologyId,
  dataset,
  selectedIri,
  onSelectConcept,
  onSelectProperty,
  onSelectIndividual,
  propertyFilter,
  onPropertyFilterChange,
  onNewConcept,
  onNewProperty,
  onNewIndividual,
}: Props) {
  const [activeTab, setActiveTab] = useState<ActiveTab>('concepts')
  const { selectedGraphIris } = useNamedGraphs()

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

  // ── Individual query ──────────────────────────────────────────
  const individualsQuery = useQuery({
    queryKey: ['individuals', ontologyId, dataset, 1, selectedGraphIris],
    queryFn: () => listIndividuals(ontologyId, { page: 1, pageSize: PAGE_SIZE, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId,
  })

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
      {/* ── Sub-tab bar ────────────────────────────────────────── */}
      <div
        className="flex flex-shrink-0 border-b"
        style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
      >
        {(['concepts', 'properties', 'individuals'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 py-2 text-xs font-semibold transition-colors"
            style={{
              color: activeTab === tab ? 'var(--color-primary)' : 'var(--color-text-muted)',
              borderBottom: activeTab === tab ? '2px solid var(--color-primary)' : '2px solid transparent',
              marginBottom: '-1px',
            }}
          >
            {tab === 'concepts' ? 'Concepts' : tab === 'properties' ? 'Properties' : 'Individuals'}
          </button>
        ))}
      </div>

      {/* ── Tab content ───────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto flex flex-col min-h-0">

        {/* ══ Concepts Tab ══════════════════════════════════════ */}
        <div
          data-testid="schema-concepts-section"
          className="flex flex-col flex-1 min-h-0"
          style={{ display: activeTab === 'concepts' ? 'flex' : 'none' }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-1 px-3 py-2 border-b flex-shrink-0"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <span className="text-xs font-medium flex-1" style={{ color: 'var(--color-text-secondary)' }}>
              Concepts
            </span>
            <button
              onClick={onNewConcept}
              className="flex items-center gap-0.5 px-2 py-1 rounded text-xs font-medium hover:opacity-80"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              <Plus size={11} />
              New Concept
            </button>
          </div>

          {/* Concept tree */}
          <div className="flex-1 min-h-0" style={{ minHeight: '160px' }}>
            <ConceptTreeView
              ontologyId={ontologyId}
              dataset={dataset}
              selectedIri={selectedIri}
              onSelect={onSelectConcept}
            />
          </div>
        </div>

        {/* ══ Properties Tab ════════════════════════════════════ */}
        <div
          data-testid="schema-properties-section"
          className="flex flex-col flex-1 min-h-0"
          style={{ display: activeTab === 'properties' ? 'flex' : 'none' }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-1 px-3 py-2 border-b flex-shrink-0"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <span className="text-xs font-medium flex-1" style={{ color: 'var(--color-text-secondary)' }}>
              Properties
              {propTotal > 0 && (
                <span className="ml-1" style={{ color: 'var(--color-text-muted)' }}>
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
          <div className="flex-1 overflow-y-auto">
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
        </div>

        {/* ══ Individuals Tab ═══════════════════════════════════ */}
        <div
          data-testid="schema-individuals-section"
          className="flex flex-col flex-1 min-h-0"
          style={{ display: activeTab === 'individuals' ? 'flex' : 'none' }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-1 px-3 py-2 border-b flex-shrink-0"
            style={{ borderColor: 'var(--color-border)' }}
          >
            <span className="text-xs font-medium flex-1" style={{ color: 'var(--color-text-secondary)' }}>
              Individuals
              {individualsQuery.data && individualsQuery.data.total > 0 && (
                <span className="ml-1" style={{ color: 'var(--color-text-muted)' }}>
                  ({individualsQuery.data.total})
                </span>
              )}
            </span>
            <button
              onClick={onNewIndividual}
              className="flex items-center gap-0.5 px-2 py-1 rounded text-xs font-medium hover:opacity-80"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              <Plus size={11} />
              New Individual
            </button>
          </div>

          {/* Individual list */}
          <div className="flex-1 overflow-y-auto">
            {individualsQuery.isLoading && (
              <div className="flex justify-center py-6">
                <LoadingSpinner size="sm" />
              </div>
            )}
            {!individualsQuery.isLoading && (individualsQuery.data?.items ?? []).length === 0 && (
              <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                No individuals
              </div>
            )}
            {(individualsQuery.data?.items ?? []).map((ind: Individual) => {
              const label = ind.label || localName(ind.iri)
              const isSelected = selectedIri === ind.iri
              const typeName = ind.types[0] ? localName(ind.types[0]) : null

              return (
                <div
                  key={ind.iri}
                  onClick={() => onSelectIndividual(ind.iri)}
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
                  title={ind.iri}
                >
                  <div
                    className="text-sm font-medium truncate"
                    style={{ color: isSelected ? 'var(--color-primary)' : 'var(--color-text-primary)' }}
                  >
                    {label}
                  </div>
                  {typeName && (
                    <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>
                      {typeName}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

      </div>
    </div>
  )
}
