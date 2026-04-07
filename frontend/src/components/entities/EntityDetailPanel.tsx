import { useState } from 'react'
import { X, Edit2, Trash2 } from 'lucide-react'
import IRIBadge from '@/components/shared/IRIBadge'
import ProvenancePanel from '@/components/provenance/ProvenancePanel'
import type { Concept } from '@/types/concept'
import type { Individual } from '@/types/individual'

interface EntityDetailPanelProps {
  entity?: Concept | Individual | null
  iri?: string | null
  onClose?: () => void
  onEdit?: () => void
  onDelete?: () => void
  /** true이면 aside 래퍼 없이 내용만 렌더링 (EntityRightPanel 내 임베딩용) */
  embedded?: boolean
}

function isConcept(e: Concept | Individual): e is Concept {
  return 'super_classes' in e
}

export default function EntityDetailPanel({ entity, iri, onClose, onEdit, onDelete, embedded }: EntityDetailPanelProps) {
  const [tab, setTab] = useState<'details' | 'provenance'>('details')
  const [confirmDelete, setConfirmDelete] = useState(false)

  const displayIri = entity?.iri ?? iri
  if (!displayIri) return null

  const Wrapper = embedded ? 'div' : 'aside'
  const wrapperClass = embedded
    ? 'flex flex-col overflow-hidden'
    : 'w-96 flex flex-col border-l overflow-hidden'
  const wrapperStyle = embedded
    ? {}
    : { backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }

  return (
    <Wrapper className={wrapperClass} style={wrapperStyle}>
      {/* Header — embedded 시 Close 버튼 숨김 */}
      {!embedded && (
        <div
          className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
            Entity Detail
          </h3>
          <div className="flex items-center gap-2">
            {onEdit && (
              <button onClick={onEdit} className="p-1 rounded hover:opacity-80"
                style={{ color: 'var(--color-text-secondary)' }} title="Edit">
                <Edit2 size={14} />
              </button>
            )}
            {onDelete && !confirmDelete && (
              <button onClick={() => setConfirmDelete(true)} className="p-1 rounded hover:opacity-80"
                style={{ color: 'var(--color-error, #ef4444)' }} title="Delete">
                <Trash2 size={14} />
              </button>
            )}
            {onDelete && confirmDelete && (
              <div className="flex items-center gap-1">
                <span className="text-xs" style={{ color: 'var(--color-error, #ef4444)' }}>Delete?</span>
                <button onClick={() => { onDelete(); setConfirmDelete(false) }}
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{ backgroundColor: 'var(--color-error, #ef4444)', color: '#fff' }}>Yes</button>
                <button onClick={() => setConfirmDelete(false)}
                  className="px-2 py-0.5 rounded text-xs"
                  style={{ color: 'var(--color-text-secondary)' }}>No</button>
              </div>
            )}
            <button onClick={onClose} className="p-1 rounded hover:opacity-80"
              style={{ color: 'var(--color-text-secondary)' }} title="Close">
              <X size={14} />
            </button>
          </div>
        </div>
      )}
      {/* embedded 모드: Edit / Delete 툴바 */}
      {embedded && (onEdit || onDelete) && (
        <div className="flex items-center gap-1.5 px-3 py-2 flex-shrink-0"
             style={{ borderBottom: '1px solid var(--color-border)' }}>
          {onEdit && (
            <button onClick={onEdit}
              className="flex items-center gap-1 px-2 py-1 rounded text-xs hover:opacity-80"
              style={{ background: 'var(--color-primary)', color: '#fff' }}>
              <Edit2 size={10} /> Edit
            </button>
          )}
          {onDelete && !confirmDelete && (
            <button onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-1 px-2 py-1 rounded text-xs hover:opacity-80"
              style={{ background: 'var(--color-error, #ef4444)', color: '#fff' }}>
              <Trash2 size={10} /> Delete
            </button>
          )}
          {onDelete && confirmDelete && (
            <div className="flex items-center gap-1">
              <span className="text-xs" style={{ color: 'var(--color-error, #ef4444)' }}>Delete?</span>
              <button onClick={() => { onDelete(); setConfirmDelete(false) }}
                className="px-2 py-0.5 rounded text-xs font-medium"
                style={{ backgroundColor: 'var(--color-error, #ef4444)', color: '#fff' }}>Yes</button>
              <button onClick={() => setConfirmDelete(false)}
                className="px-2 py-0.5 rounded text-xs"
                style={{ color: 'var(--color-text-secondary)' }}>No</button>
            </div>
          )}
        </div>
      )}

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
                    {(entity.super_classes?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Parent Classes
                        </label>
                        <div className="flex flex-wrap gap-1">
                          {entity.super_classes.map((p) => (
                            <IRIBadge key={p} iri={p} />
                          ))}
                        </div>
                      </div>
                    )}
                    {(entity.equivalent_classes?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Equivalent Classes
                        </label>
                        <div className="flex flex-wrap gap-1">
                          {entity.equivalent_classes.map((c) => (
                            <IRIBadge key={c} iri={c} />
                          ))}
                        </div>
                      </div>
                    )}
                    {(entity.disjoint_with?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Disjoint With
                        </label>
                        <div className="flex flex-wrap gap-1">
                          {entity.disjoint_with.map((c) => (
                            <IRIBadge key={c} iri={c} />
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
                    {(entity.restrictions?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Restrictions ({entity.restrictions?.length})
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
                              <span style={{ color: 'var(--color-text-muted)' }}>{r.type} </span>
                              <IRIBadge iri={r.property_iri} />
                              {r.value && <> → <span className="font-mono">{r.value}</span></>}
                              {r.cardinality !== undefined && <span> ({r.cardinality})</span>}
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
                    {(entity.types?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Types
                        </label>
                        <div className="flex flex-wrap gap-1">
                          {entity.types.map((t) => (
                            <IRIBadge key={t} iri={t} />
                          ))}
                        </div>
                      </div>
                    )}
                    {(entity.data_property_values?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Data Properties
                        </label>
                        <div className="flex flex-col gap-1">
                          {entity.data_property_values.map((dp, i) => (
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
                    {(entity.object_property_values?.length ?? 0) > 0 && (
                      <div>
                        <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                          Object Properties
                        </label>
                        <div className="flex flex-col gap-1">
                          {entity.object_property_values.map((op, i) => (
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
    </Wrapper>
  )
}
