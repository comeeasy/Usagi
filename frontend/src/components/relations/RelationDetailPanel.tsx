import { useState } from 'react'
import { X, Edit2 } from 'lucide-react'
import IRIBadge from '@/components/shared/IRIBadge'
import type { ObjectProperty, DataProperty } from '@/types/property'

type AnyProperty = ObjectProperty | DataProperty

function isObjectProperty(p: AnyProperty): p is ObjectProperty {
  return 'characteristics' in p
}

interface RelationDetailPanelProps {
  property?: AnyProperty | null
  iri?: string | null
  onClose?: () => void
  onEdit?: () => void
}

export default function RelationDetailPanel({ property, iri, onClose, onEdit }: RelationDetailPanelProps) {
  const displayIri = property?.iri ?? iri
  if (!displayIri) return null

  return (
    <aside
      className="w-80 flex flex-col border-l overflow-hidden"
      style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          Property Detail
        </h3>
        <div className="flex items-center gap-2">
          {onEdit && (
            <button onClick={onEdit} className="p-1 rounded hover:opacity-80" style={{ color: 'var(--color-text-secondary)' }}>
              <Edit2 size={14} />
            </button>
          )}
          <button onClick={onClose} className="p-1 rounded hover:opacity-80" style={{ color: 'var(--color-text-secondary)' }}>
            <X size={14} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Type badge */}
        {property && (
          <span
            className="self-start text-xs px-2 py-1 rounded-full font-medium"
            style={{
              backgroundColor: isObjectProperty(property) ? 'rgba(163,113,247,0.2)' : 'rgba(210,153,34,0.2)',
              color: isObjectProperty(property) ? '#A371F7' : 'var(--color-warning)',
            }}
          >
            {isObjectProperty(property) ? 'Object Property' : 'Data Property'}
          </span>
        )}

        <div>
          <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>IRI</label>
          <IRIBadge iri={displayIri} showCopy />
        </div>

        {property?.label && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Label</label>
            <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>{property.label}</p>
          </div>
        )}

        {property?.comment && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Comment</label>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>{property.comment}</p>
          </div>
        )}

        {property && property.domain.length > 0 && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Domain</label>
            <div className="flex flex-wrap gap-1">
              {property.domain.map((d) => <IRIBadge key={d} iri={d} />)}
            </div>
          </div>
        )}

        {property && property.range.length > 0 && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Range</label>
            <div className="flex flex-wrap gap-1">
              {property.range.map((r) => (
                <span key={r} className="font-mono text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-info)' }}>
                  {r}
                </span>
              ))}
            </div>
          </div>
        )}

        {property && isObjectProperty(property) && property.characteristics.length > 0 && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Characteristics</label>
            <div className="flex flex-wrap gap-1">
              {property.characteristics.map((c) => (
                <span key={c} className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}

        {property && isObjectProperty(property) && property.inverseOf && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Inverse Of</label>
            <IRIBadge iri={property.inverseOf} />
          </div>
        )}
      </div>
    </aside>
  )
}
