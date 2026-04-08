/**
 * SchemaDetailPanel — Schema 탭 우측 Detail 패널
 *
 * - Concept 선택 시: [Detail] [Relations] [Instances] 서브탭
 *     Detail    → EntityDetailPanel (embedded)
 *     Relations → "as domain" / "as range" property 목록
 *     Instances → IndividualsSidebar (inline)
 *
 * - Property 선택 시: 단일 뷰
 *     type, IRI, label, Domain(클릭 가능), Range, Characteristics
 *
 * - 미선택: placeholder
 */
import { useState } from 'react'
import { Edit2, Trash2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getConcept } from '@/api/entities'
import { searchRelations } from '@/api/relations'
import EntityDetailPanel from '@/components/entities/EntityDetailPanel'
import IndividualsSidebar from '@/components/graph/IndividualsSidebar'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import IRIBadge from '@/components/shared/IRIBadge'
import type { ObjectProperty, DataProperty } from '@/types/property'
import type { Concept } from '@/types/concept'

type RightSubTab = 'detail' | 'relations' | 'instances'

function isObjectProperty(p: ObjectProperty | DataProperty): p is ObjectProperty {
  return 'characteristics' in p
}

function localName(iri: string): string {
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}

interface Props {
  ontologyId: string
  dataset: string
  selectedIri: string | null
  selectedKind: 'concept' | 'property' | null
  selectedProperty?: ObjectProperty | DataProperty | null
  onNavigateToConcept: (iri: string) => void
  onEdit?: () => void
  onDelete?: () => void
}

export default function SchemaDetailPanel({
  ontologyId,
  dataset,
  selectedIri,
  selectedKind,
  selectedProperty,
  onNavigateToConcept,
  onEdit,
  onDelete,
}: Props) {
  const [subTab, setSubTab] = useState<RightSubTab>('detail')

  // ── Concept 데이터 ────────────────────────────────────────────
  const conceptQuery = useQuery<Concept>({
    queryKey: ['entity', ontologyId, dataset, selectedIri, 'concepts'],
    queryFn: () => getConcept(ontologyId, selectedIri!, dataset),
    enabled: !!selectedIri && selectedKind === 'concept',
  })

  // ── Relations 탭: domain/range 조회 ───────────────────────────
  const domainQuery = useQuery({
    queryKey: ['relations-as-domain', ontologyId, selectedIri, dataset],
    queryFn: () => searchRelations(ontologyId, '', selectedIri!, undefined, 50, dataset),
    enabled: !!selectedIri && selectedKind === 'concept' && subTab === 'relations',
  })

  const rangeQuery = useQuery({
    queryKey: ['relations-as-range', ontologyId, selectedIri, dataset],
    queryFn: () => searchRelations(ontologyId, '', undefined, selectedIri!, 50, dataset),
    enabled: !!selectedIri && selectedKind === 'concept' && subTab === 'relations',
  })

  // ── 미선택 placeholder ────────────────────────────────────────
  if (!selectedIri || !selectedKind) {
    return (
      <div
        className="flex-1 flex items-center justify-center"
        style={{ color: 'var(--color-text-muted)' }}
      >
        <p className="text-sm">Select a Concept or Property to view details</p>
      </div>
    )
  }

  // ════════════════════════════════════════════════════════════
  // Property 선택 뷰
  // ════════════════════════════════════════════════════════════
  if (selectedKind === 'property' && selectedProperty) {
    const isObj = isObjectProperty(selectedProperty)
    return (
      <div className="flex flex-col overflow-y-auto p-4 gap-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <span
              className="inline-block text-xs px-2 py-0.5 rounded-full font-medium mb-2"
              style={{
                backgroundColor: isObj ? 'rgba(163,113,247,0.2)' : 'rgba(210,153,34,0.2)',
                color: isObj ? '#A371F7' : 'var(--color-warning)',
              }}
            >
              {isObj ? 'Object Property' : 'Data Property'}
            </span>
            <h2 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {selectedProperty.label || localName(selectedProperty.iri)}
            </h2>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {onEdit && (
              <button
                onClick={onEdit}
                className="p-1.5 rounded hover:opacity-70"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                <Edit2 size={14} />
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="p-1.5 rounded hover:opacity-70"
                style={{ color: 'var(--color-error, #ef4444)' }}
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>

        {/* IRI */}
        <div>
          <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>IRI</label>
          <IRIBadge iri={selectedProperty.iri} showCopy />
        </div>

        {/* Comment */}
        {selectedProperty.comment && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Comment</label>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{selectedProperty.comment}</p>
          </div>
        )}

        {/* Domain — 클릭 시 해당 Concept으로 포커스 */}
        <div>
          <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Domain</label>
          <div className="flex flex-wrap gap-1">
            {selectedProperty.domain.length === 0 && (
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>—</span>
            )}
            {selectedProperty.domain.map((d) => (
              <button
                key={d}
                onClick={() => onNavigateToConcept(d)}
                className="font-mono text-xs px-1.5 py-0.5 rounded hover:opacity-70 transition-opacity"
                style={{
                  backgroundColor: 'var(--color-bg-elevated)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-info)',
                }}
                title={d}
              >
                {localName(d)}
              </button>
            ))}
          </div>
        </div>

        {/* Range */}
        <div>
          <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Range</label>
          <div className="flex flex-wrap gap-1">
            {selectedProperty.range.length === 0 && (
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>—</span>
            )}
            {selectedProperty.range.map((r) => (
              isObj ? (
                <button
                  key={r as string}
                  onClick={() => onNavigateToConcept(r as string)}
                  className="font-mono text-xs px-1.5 py-0.5 rounded hover:opacity-70 transition-opacity"
                  style={{
                    backgroundColor: 'var(--color-bg-elevated)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-info)',
                  }}
                  title={r as string}
                >
                  {localName(r as string)}
                </button>
              ) : (
                <span
                  key={r as string}
                  className="font-mono text-xs px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: 'var(--color-bg-elevated)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-info)',
                  }}
                >
                  {r as string}
                </span>
              )
            ))}
          </div>
        </div>

        {/* Characteristics (Object Property만) */}
        {isObj && (selectedProperty as ObjectProperty).characteristics.length > 0 && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Characteristics</label>
            <div className="flex flex-wrap gap-1">
              {(selectedProperty as ObjectProperty).characteristics.map((c) => (
                <span
                  key={c}
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: 'var(--color-bg-elevated)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Inverse Of (Object Property만) */}
        {isObj && (selectedProperty as ObjectProperty).inverseOf && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Inverse Of</label>
            <IRIBadge iri={(selectedProperty as ObjectProperty).inverseOf!} />
          </div>
        )}
      </div>
    )
  }

  // ════════════════════════════════════════════════════════════
  // Concept 선택 뷰 — [Detail] [Relations] [Instances] 탭
  // ════════════════════════════════════════════════════════════
  const SUB_TABS: { key: RightSubTab; label: string }[] = [
    { key: 'detail', label: 'Detail' },
    { key: 'relations', label: 'Relations' },
    { key: 'instances', label: 'Instances' },
  ]

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Concept name header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div>
          {conceptQuery.isLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {conceptQuery.data?.label || localName(selectedIri)}
            </h2>
          )}
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
            owl:Class
          </p>
        </div>
        <div className="flex items-center gap-1">
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1.5 rounded hover:opacity-70"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              <Edit2 size={14} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1.5 rounded hover:opacity-70"
              style={{ color: 'var(--color-error, #ef4444)' }}
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Sub-tab bar */}
      <div
        className="flex border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        {SUB_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setSubTab(key)}
            className="px-4 py-2 text-xs font-medium border-b-2 transition-colors"
            style={{
              borderBottomColor: subTab === key ? 'var(--color-primary)' : 'transparent',
              color: subTab === key ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">

        {/* ── Detail tab ── */}
        {subTab === 'detail' && (
          <EntityDetailPanel
            embedded
            entity={conceptQuery.data ?? null}
            iri={selectedIri}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        )}

        {/* ── Relations tab ── */}
        {subTab === 'relations' && (
          <div className="p-4 flex flex-col gap-4">
            {/* as domain */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-muted)' }}>
                as domain
              </h3>
              {domainQuery.isLoading && <LoadingSpinner size="sm" />}
              {domainQuery.isSuccess && domainQuery.data.length === 0 && (
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>None</p>
              )}
              {domainQuery.isSuccess && domainQuery.data.map((prop) => (
                <div
                  key={prop.iri}
                  className="flex items-center gap-2 py-1.5 border-b text-sm"
                  style={{ borderColor: 'var(--color-border)' }}
                >
                  <span
                    className="text-xs font-mono"
                    style={{ color: 'characteristics' in prop ? '#A371F7' : 'var(--color-warning)' }}
                  >
                    {'characteristics' in prop ? '≈' : '—'}
                  </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>
                    {prop.label || localName(prop.iri)}
                  </span>
                  <span className="text-xs ml-auto" style={{ color: 'var(--color-text-muted)' }}>
                    → {prop.range[0] ? localName(prop.range[0] as string) : '?'}
                  </span>
                </div>
              ))}
            </div>

            {/* as range */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-muted)' }}>
                as range
              </h3>
              {rangeQuery.isLoading && <LoadingSpinner size="sm" />}
              {rangeQuery.isSuccess && rangeQuery.data.length === 0 && (
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>None</p>
              )}
              {rangeQuery.isSuccess && rangeQuery.data.map((prop) => (
                <div
                  key={prop.iri}
                  className="flex items-center gap-2 py-1.5 border-b text-sm"
                  style={{ borderColor: 'var(--color-border)' }}
                >
                  <span
                    className="text-xs font-mono"
                    style={{ color: 'characteristics' in prop ? '#A371F7' : 'var(--color-warning)' }}
                  >
                    {'characteristics' in prop ? '≈' : '—'}
                  </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>
                    {prop.label || localName(prop.iri)}
                  </span>
                  <span className="text-xs ml-auto" style={{ color: 'var(--color-text-muted)' }}>
                    {prop.domain[0] ? localName(prop.domain[0]) : '?'} →
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Instances tab ── */}
        {subTab === 'instances' && (
          <IndividualsSidebar
            ontologyId={ontologyId}
            conceptIri={selectedIri}
            inline
          />
        )}
      </div>
    </div>
  )
}
