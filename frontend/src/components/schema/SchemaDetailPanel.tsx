/**
 * SchemaDetailPanel — Schema 탭 우측 Detail 패널
 *
 * Concept  → [Detail] [Relations] [Provenance]
 * Property → [Detail] [Provenance]
 * 미선택   → placeholder
 */
import { useState } from 'react'
import { Edit2, Trash2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getConcept } from '@/api/entities'
import { searchRelations } from '@/api/relations'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import IRIBadge from '@/components/shared/IRIBadge'
import ProvenancePanel from '@/components/provenance/ProvenancePanel'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import type { ObjectProperty, DataProperty } from '@/types/property'
import type { Concept } from '@/types/concept'

type ConceptTab = 'detail' | 'relations' | 'provenance'
type PropertyTab = 'detail' | 'provenance'

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

// ── 공통 탭 버튼 ────────────────────────────────────────────────
function TabBar<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: T; label: string }[]
  active: T
  onChange: (t: T) => void
}) {
  return (
    <div className="flex border-b flex-shrink-0" style={{ borderColor: 'var(--color-border)' }}>
      {tabs.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className="px-4 py-2 text-xs font-medium border-b-2 transition-colors"
          style={{
            borderBottomColor: active === key ? 'var(--color-primary)' : 'transparent',
            color: active === key ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// ── 섹션 레이블 ────────────────────────────────────────────────
function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
      {children}
    </label>
  )
}

// ── IRI 배지 목록 ──────────────────────────────────────────────
function IriBadgeList({ iris, onNavigate }: { iris: string[]; onNavigate?: (iri: string) => void }) {
  if (iris.length === 0) return <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {iris.map((iri) =>
        onNavigate ? (
          <button
            key={iri}
            onClick={() => onNavigate(iri)}
            className="font-mono text-xs px-1.5 py-0.5 rounded hover:opacity-70 transition-opacity"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-info)',
            }}
            title={iri}
          >
            {localName(iri)}
          </button>
        ) : (
          <IRIBadge key={iri} iri={iri} />
        ),
      )}
    </div>
  )
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
  const [conceptTab, setConceptTab] = useState<ConceptTab>('detail')
  const [propertyTab, setPropertyTab] = useState<PropertyTab>('detail')
  const { selectedGraphIris } = useNamedGraphs()

  // ── Concept 데이터 ────────────────────────────────────────────
  const conceptQuery = useQuery<Concept>({
    queryKey: ['entity', ontologyId, dataset, selectedIri, 'concepts'],
    queryFn: () => getConcept(ontologyId, selectedIri!, dataset),
    enabled: !!selectedIri && selectedKind === 'concept',
  })

  // ── Relations 탭: domain/range 조회 ───────────────────────────
  const domainQuery = useQuery({
    queryKey: ['relations-as-domain', ontologyId, selectedIri, dataset, selectedGraphIris],
    queryFn: () => searchRelations(ontologyId, '', selectedIri!, undefined, 50, dataset, selectedGraphIris),
    enabled: !!selectedIri && selectedKind === 'concept' && conceptTab === 'relations',
  })

  const rangeQuery = useQuery({
    queryKey: ['relations-as-range', ontologyId, selectedIri, dataset, selectedGraphIris],
    queryFn: () => searchRelations(ontologyId, '', undefined, selectedIri!, 50, dataset, selectedGraphIris),
    enabled: !!selectedIri && selectedKind === 'concept' && conceptTab === 'relations',
  })

  // ── 미선택 placeholder ────────────────────────────────────────
  if (!selectedIri || !selectedKind) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--color-text-muted)' }}>
        <p className="text-sm">Select a Concept or Property to view details</p>
      </div>
    )
  }

  // ════════════════════════════════════════════════════════════
  // Property 선택 뷰 — [Detail] [Provenance]
  // ════════════════════════════════════════════════════════════
  if (selectedKind === 'property' && selectedProperty) {
    const isObj = isObjectProperty(selectedProperty)
    const objProp = selectedProperty as ObjectProperty
    const dataProp = selectedProperty as DataProperty

    return (
      <div className="flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div
          className="flex items-start justify-between gap-2 px-4 py-3 border-b flex-shrink-0"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div>
            <span
              className="inline-block text-xs px-2 py-0.5 rounded-full font-medium mb-1"
              style={{
                backgroundColor: isObj ? 'rgba(163,113,247,0.2)' : 'rgba(210,153,34,0.2)',
                color: isObj ? '#A371F7' : 'var(--color-warning)',
              }}
            >
              {isObj ? 'Object Property' : 'Data Property'}
            </span>
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {selectedProperty.label || localName(selectedProperty.iri)}
            </h2>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            {onEdit && (
              <button onClick={onEdit} className="p-1.5 rounded hover:opacity-70" style={{ color: 'var(--color-text-secondary)' }}>
                <Edit2 size={14} />
              </button>
            )}
            {onDelete && (
              <button onClick={onDelete} className="p-1.5 rounded hover:opacity-70" style={{ color: 'var(--color-error, #ef4444)' }}>
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>

        <TabBar
          tabs={[
            { key: 'detail' as PropertyTab, label: 'Detail' },
            { key: 'provenance' as PropertyTab, label: 'Provenance' },
          ]}
          active={propertyTab}
          onChange={setPropertyTab}
        />

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          {propertyTab === 'detail' && (
            <>
              {/* IRI */}
              <div>
                <FieldLabel>IRI</FieldLabel>
                <IRIBadge iri={selectedProperty.iri} showCopy />
              </div>

              {/* Comment */}
              {selectedProperty.comment && (
                <div>
                  <FieldLabel>Comment</FieldLabel>
                  <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{selectedProperty.comment}</p>
                </div>
              )}

              {/* Domain */}
              <div>
                <FieldLabel>Domain</FieldLabel>
                <IriBadgeList iris={selectedProperty.domain} onNavigate={onNavigateToConcept} />
              </div>

              {/* Range */}
              <div>
                <FieldLabel>Range</FieldLabel>
                {selectedProperty.range.length === 0 ? (
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>—</span>
                ) : (
                  <div className="flex flex-wrap gap-1">
                    {selectedProperty.range.map((r) =>
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
                      ),
                    )}
                  </div>
                )}
              </div>

              {/* Super Properties */}
              {(selectedProperty as ObjectProperty).superProperties?.length > 0 && (
                <div>
                  <FieldLabel>Super Properties</FieldLabel>
                  <IriBadgeList iris={(selectedProperty as ObjectProperty).superProperties} />
                </div>
              )}

              {/* Characteristics (Object only) */}
              {isObj && objProp.characteristics.length > 0 && (
                <div>
                  <FieldLabel>Characteristics</FieldLabel>
                  <div className="flex flex-wrap gap-1">
                    {objProp.characteristics.map((c) => (
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

              {/* Inverse Of (Object only) */}
              {isObj && objProp.inverseOf && (
                <div>
                  <FieldLabel>Inverse Of</FieldLabel>
                  <IRIBadge iri={objProp.inverseOf} />
                </div>
              )}

              {/* isFunctional (Data only) */}
              {!isObj && (
                <div>
                  <FieldLabel>Functional</FieldLabel>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: dataProp.isFunctional ? 'rgba(63,185,80,0.15)' : 'var(--color-bg-elevated)',
                      border: '1px solid var(--color-border)',
                      color: dataProp.isFunctional ? '#3FB950' : 'var(--color-text-muted)',
                    }}
                  >
                    {dataProp.isFunctional ? 'Functional' : 'Not functional'}
                  </span>
                </div>
              )}
            </>
          )}

          {propertyTab === 'provenance' && (
            <ProvenancePanel records={[]} />
          )}
        </div>
      </div>
    )
  }

  // ════════════════════════════════════════════════════════════
  // Concept 선택 뷰 — [Detail] [Relations] [Provenance]
  // ════════════════════════════════════════════════════════════
  const concept = conceptQuery.data

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div>
          {conceptQuery.isLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {concept?.label || localName(selectedIri)}
            </h2>
          )}
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>owl:Class</p>
        </div>
        <div className="flex items-center gap-1">
          {onEdit && (
            <button onClick={onEdit} className="p-1.5 rounded hover:opacity-70" style={{ color: 'var(--color-text-secondary)' }}>
              <Edit2 size={14} />
            </button>
          )}
          {onDelete && (
            <button onClick={onDelete} className="p-1.5 rounded hover:opacity-70" style={{ color: 'var(--color-error, #ef4444)' }}>
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      <TabBar
        tabs={[
          { key: 'detail' as ConceptTab, label: 'Detail' },
          { key: 'relations' as ConceptTab, label: 'Relations' },
          { key: 'provenance' as ConceptTab, label: 'Provenance' },
        ]}
        active={conceptTab}
        onChange={setConceptTab}
      />

      <div className="flex-1 overflow-y-auto">

        {/* ── Detail tab ── */}
        {conceptTab === 'detail' && (
          <div className="p-4 flex flex-col gap-4">
            {/* IRI */}
            <div>
              <FieldLabel>IRI</FieldLabel>
              <IRIBadge iri={selectedIri} showCopy />
            </div>

            {concept && (
              <>
                {/* Comment */}
                {concept.comment && (
                  <div>
                    <FieldLabel>Comment</FieldLabel>
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{concept.comment}</p>
                  </div>
                )}

                {/* Counts */}
                <div className="flex gap-4">
                  <div>
                    <FieldLabel>Instances</FieldLabel>
                    <span className="text-sm font-mono" style={{ color: 'var(--color-text-primary)' }}>
                      {concept.individual_count ?? 0}
                    </span>
                  </div>
                  <div>
                    <FieldLabel>Subclasses</FieldLabel>
                    <span className="text-sm font-mono" style={{ color: 'var(--color-text-primary)' }}>
                      {concept.subclass_count ?? 0}
                    </span>
                  </div>
                  {concept.is_deprecated && (
                    <div className="flex items-end">
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: 'rgba(239,68,68,0.15)',
                          border: '1px solid var(--color-border)',
                          color: 'var(--color-error)',
                        }}
                      >
                        Deprecated
                      </span>
                    </div>
                  )}
                </div>

                {/* Parent Classes */}
                {concept.super_classes.length > 0 && (
                  <div>
                    <FieldLabel>Parent Classes</FieldLabel>
                    <IriBadgeList iris={concept.super_classes} onNavigate={onNavigateToConcept} />
                  </div>
                )}

                {/* Equivalent Classes */}
                {concept.equivalent_classes?.length > 0 && (
                  <div>
                    <FieldLabel>Equivalent Classes</FieldLabel>
                    <IriBadgeList iris={concept.equivalent_classes} />
                  </div>
                )}

                {/* Disjoint With */}
                {concept.disjoint_with?.length > 0 && (
                  <div>
                    <FieldLabel>Disjoint With</FieldLabel>
                    <IriBadgeList iris={concept.disjoint_with} />
                  </div>
                )}

                {/* Restrictions */}
                {concept.restrictions?.length > 0 && (
                  <div>
                    <FieldLabel>Restrictions ({concept.restrictions.length})</FieldLabel>
                    <div className="flex flex-col gap-1">
                      {concept.restrictions.map((r, i) => (
                        <div
                          key={i}
                          className="text-xs p-2 rounded flex flex-wrap items-center gap-1"
                          style={{ backgroundColor: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }}
                        >
                          <span style={{ color: 'var(--color-text-muted)' }}>{r.type}</span>
                          <IRIBadge iri={r.property_iri} />
                          {r.value && <><span>→</span><span className="font-mono">{r.value}</span></>}
                          {r.cardinality !== undefined && <span>({r.cardinality})</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Properties (raw predicates) */}
                {concept.properties?.length > 0 && (
                  <div>
                    <FieldLabel>Properties ({concept.properties.length})</FieldLabel>
                    <div className="flex flex-col gap-1">
                      {concept.properties.map((pv, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 text-xs py-1 border-b"
                          style={{ borderColor: 'var(--color-border)' }}
                        >
                          <span
                            className="font-mono truncate"
                            style={{ color: 'var(--color-warning)', maxWidth: '50%' }}
                            title={pv.predicate}
                          >
                            {localName(pv.predicate)}
                          </span>
                          <span style={{ color: 'var(--color-text-muted)' }}>:</span>
                          <span
                            className="truncate"
                            style={{
                              color: pv.value_type === 'uri' ? 'var(--color-info)' : 'var(--color-text-primary)',
                              fontFamily: pv.value_type === 'uri' ? 'monospace' : undefined,
                            }}
                            title={pv.value}
                          >
                            {pv.value_type === 'uri' ? localName(pv.value) : pv.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {!concept && conceptQuery.isLoading && (
              <div className="flex justify-center py-6"><LoadingSpinner size="sm" /></div>
            )}
          </div>
        )}

        {/* ── Relations tab ── */}
        {conceptTab === 'relations' && (
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
                  <span className="text-xs font-mono" style={{ color: 'characteristics' in prop ? '#A371F7' : 'var(--color-warning)' }}>
                    {'characteristics' in prop ? '≈' : '—'}
                  </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>{prop.label || localName(prop.iri)}</span>
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
                  <span className="text-xs font-mono" style={{ color: 'characteristics' in prop ? '#A371F7' : 'var(--color-warning)' }}>
                    {'characteristics' in prop ? '≈' : '—'}
                  </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>{prop.label || localName(prop.iri)}</span>
                  <span className="text-xs ml-auto" style={{ color: 'var(--color-text-muted)' }}>
                    {prop.domain[0] ? localName(prop.domain[0]) : '?'} →
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Provenance tab ── */}
        {conceptTab === 'provenance' && (
          <div className="p-4">
            <ProvenancePanel records={[]} />
          </div>
        )}

      </div>
    </div>
  )
}
