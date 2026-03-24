import { useState } from 'react'
import { X, Edit2 } from 'lucide-react'
import IRIBadge from '@/components/shared/IRIBadge'
import ProvenancePanel from '@/components/provenance/ProvenancePanel'
import type { Concept } from '@/types/concept'
import type { Individual } from '@/types/individual'

interface EntityDetailPanelProps {
  entity?: Concept | Individual | null
  iri?: string | null
  onClose?: () => void
  onEdit?: () => void
}

function isConcept(e: Concept | Individual): e is Concept {
  return 'parent_iris' in e
}

export default function EntityDetailPanel({ entity, iri, onClose, onEdit }: EntityDetailPanelProps) {
  const [tab, setTab] = useState<'details' | 'provenance'>('details')

  const displayIri = entity?.iri ?? iri
  if (!displayIri) return null

  return (
    <aside
      className="w-96 flex flex-col border-l overflow-hidden"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          Entity Detail
        </h3>
        <div className="flex items-center gap-2">
          {onEdit && (
            <button
              onClick={onEdit}
              className="p-1 rounded hover:opacity-80"
              style={{ color: 'var(--color-text-secondary)' }}
              title="Edit"
            >
              <Edit2 size={14} />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1 rounded hover:opacity-80"
            style={{ color: 'var(--color-text-secondary)' }}
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        {(['details', 'provenance'] as const).map((t) => (
          <button
            key={t}
            className="px-4 py-2 text-sm border-b-2 transition-colors capitalize"
            style={{
              borderColor: tab === t ? 'var(--color-primary)' : 'transparent',
              color: tab === t ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            }}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'details' && (
          <div className="flex flex-col gap-4">
            {/* IRI */}
            <div>
              <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                IRI
              </label>
              <IRIBadge iri={displayIri} showCopy />
            </div>

            {entity && (
              <>
                {/* Label */}
                {entity.label && (
                  <div>
                    <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                      Label
                    </label>
                    <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
                      {entity.label}
                    </p>
                  </div>
                )}

                {/* Concept-specific */}
                {isConcept(entity) && (
                  <>
                    {entity.parent_iris.length > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Parent Classes
                        </label>
                        <div className="flex flex-wrap gap-1">
                          {entity.parent_iris.map((p) => (
                            <IRIBadge key={p} iri={p} />
                          ))}
                        </div>
                      </div>
                    )}
                    {entity.comment && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Comment
                        </label>
                        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                          {entity.comment}
                        </p>
                      </div>
                    )}
                    {entity.restrictions.length > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Restrictions ({entity.restrictions.length})
                        </label>
                        <div className="flex flex-col gap-1">
                          {entity.restrictions.map((r, i) => (
                            <div
                              key={i}
                              className="text-xs p-2 rounded"
                              style={{
                                backgroundColor: 'var(--color-bg-elevated)',
                                color: 'var(--color-text-secondary)',
                              }}
                            >
                              <span style={{ color: 'var(--color-text-muted)' }}>{r.restriction_type} </span>
                              <IRIBadge iri={r.property_iri} />
                              {r.filler_iri && <> → <IRIBadge iri={r.filler_iri} /></>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* Individual-specific */}
                {!isConcept(entity) && (
                  <>
                    {entity.type_iris.length > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Types
                        </label>
                        <div className="flex flex-wrap gap-1">
                          {entity.type_iris.map((t) => (
                            <IRIBadge key={t} iri={t} />
                          ))}
                        </div>
                      </div>
                    )}
                    {entity.data_properties.length > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Data Properties
                        </label>
                        <div className="flex flex-col gap-1">
                          {entity.data_properties.map((dp, i) => (
                            <div key={i} className="text-xs flex gap-2 items-center">
                              <IRIBadge iri={dp.property_iri} />
                              <span style={{ color: 'var(--color-text-primary)' }}>
                                {String(dp.value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {entity.object_properties.length > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Object Properties
                        </label>
                        <div className="flex flex-col gap-1">
                          {entity.object_properties.map((op, i) => (
                            <div key={i} className="text-xs flex gap-2 items-center">
                              <IRIBadge iri={op.property_iri} />
                              <span style={{ color: 'var(--color-text-muted)' }}>→</span>
                              <IRIBadge iri={op.target_iri} />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </>
            )}

            {!entity && (
              <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Loading entity details...
              </p>
            )}
          </div>
        )}

        {tab === 'provenance' && !isConcept(entity as Concept | Individual) && (
          <ProvenancePanel records={(entity as Individual)?.provenance ?? []} />
        )}
        {tab === 'provenance' && entity && isConcept(entity) && (
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            No provenance data for concepts.
          </p>
        )}
      </div>
    </aside>
  )
}
