import { X, Pencil, Trash2 } from 'lucide-react'
import IRIBadge from '@/components/shared/IRIBadge'

interface NodeData {
  id: string
  label?: string
  type?: string
  iri?: string
  [key: string]: unknown
}

interface NodeDetailPanelProps {
  nodeId?: string | null
  nodeData?: NodeData | null
  onClose?: () => void
  onEdit?: () => void
  onDelete?: () => void
}

export default function NodeDetailPanel({ nodeId, nodeData, onClose, onEdit, onDelete }: NodeDetailPanelProps) {
  if (!nodeId) return null

  const iri = nodeData?.iri ?? nodeId

  return (
    <aside
      className="w-72 flex flex-col border-l overflow-hidden"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      <div
        className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          Node Detail
        </h3>
        <button
          onClick={onClose}
          className="p-1 rounded hover:opacity-80"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Type badge */}
        {nodeData?.type && (
          <div>
            <span
              className="text-xs px-2 py-1 rounded-full font-medium"
              style={{
                backgroundColor:
                  nodeData.type === 'concept'
                    ? 'rgba(47,129,247,0.2)'
                    : 'rgba(63,185,80,0.2)',
                color:
                  nodeData.type === 'concept'
                    ? 'var(--color-primary)'
                    : 'var(--color-success)',
              }}
            >
              {nodeData.type === 'concept' ? 'Concept' : 'Individual'}
            </span>
          </div>
        )}

        {/* IRI */}
        <div>
          <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
            IRI
          </label>
          <IRIBadge iri={iri} showCopy />
        </div>

        {/* Label */}
        {nodeData?.label && (
          <div>
            <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
              Label
            </label>
            <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
              {nodeData.label}
            </p>
          </div>
        )}

        {/* Additional data */}
        {nodeData && Object.entries(nodeData)
          .filter(([k]) => !['id', 'label', 'type', 'iri'].includes(k))
          .map(([k, v]) => (
            <div key={k}>
              <label className="text-xs block mb-1 capitalize" style={{ color: 'var(--color-text-muted)' }}>
                {k}
              </label>
              <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                {String(v)}
              </p>
            </div>
          ))}

        {/* Actions */}
        {(onEdit || onDelete) && (
          <div className="flex gap-2 pt-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
            {onEdit && (
              <button
                onClick={onEdit}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium hover:opacity-80 flex-1"
                style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              >
                <Pencil size={12} />
                Edit
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium hover:opacity-80 flex-1"
                style={{ backgroundColor: 'var(--color-error, #ef4444)', color: '#fff' }}
              >
                <Trash2 size={12} />
                Delete
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
