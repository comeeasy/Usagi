import { RefreshCw, Edit2, Trash2, Circle, Upload } from 'lucide-react'
import type { BackingSource } from '@/types/source'

interface SourceListProps {
  sources?: BackingSource[]
  onEdit?: (sourceId: string) => void
  onDelete?: (sourceId: string) => void
  onSync?: (sourceId: string) => void
  onUpload?: (sourceId: string) => void
}

const SOURCE_TYPE_COLORS: Record<string, string> = {
  jdbc: '#2F81F7',
  api: '#3FB950',
  stream: '#D29922',
  'csv-file': '#A78BFA',
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  jdbc: 'JDBC',
  api: 'API',
  stream: 'Stream',
  'csv-file': 'CSV',
}

export default function SourceList({ sources = [], onEdit, onDelete, onSync, onUpload }: SourceListProps) {
  if (sources.length === 0) {
    return (
      <div
        className="flex items-center justify-center py-12 text-sm rounded-lg border"
        style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-surface)' }}
      >
        No backing sources configured
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      {sources.map((source) => (
        <div
          key={source.id}
          className="flex items-center justify-between p-3 rounded-lg border"
          style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Circle
              size={8}
              fill={source.status === 'active' ? 'var(--color-success)' : 'var(--color-text-muted)'}
              style={{ color: source.status === 'active' ? 'var(--color-success)' : 'var(--color-text-muted)', flexShrink: 0 }}
            />

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>
                  {source.label}
                </span>
                <span
                  className="text-xs px-1.5 py-0.5 rounded font-semibold"
                  style={{
                    backgroundColor: `${SOURCE_TYPE_COLORS[source.source_type] ?? '#8B949E'}20`,
                    color: SOURCE_TYPE_COLORS[source.source_type] ?? 'var(--color-text-muted)',
                  }}
                >
                  {SOURCE_TYPE_LABELS[source.source_type] ?? source.source_type}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="text-xs font-mono truncate" style={{ color: 'var(--color-text-muted)' }}>
                  {source.concept_iri}
                </span>
                {source.last_sync_at && (
                  <span className="text-xs flex-shrink-0" style={{ color: 'var(--color-text-muted)' }}>
                    Last sync: {new Date(source.last_sync_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0 ml-2">
            {source.source_type === 'csv-file' ? (
              <button
                onClick={() => onUpload?.(source.id)}
                className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium hover:opacity-80 transition-opacity"
                style={{ backgroundColor: 'rgba(167,139,250,0.15)', color: '#A78BFA', border: '1px solid rgba(167,139,250,0.3)' }}
                title="Upload CSV file"
              >
                <Upload size={11} />
                Upload CSV
              </button>
            ) : (
              <button
                onClick={() => onSync?.(source.id)}
                className="p-1.5 rounded hover:opacity-80 transition-opacity"
                style={{ color: 'var(--color-primary)' }}
                title="Sync now"
              >
                <RefreshCw size={14} />
              </button>
            )}
            <button
              onClick={() => onEdit?.(source.id)}
              className="p-1.5 rounded hover:opacity-80 transition-opacity"
              style={{ color: 'var(--color-text-secondary)' }}
              title="Edit"
            >
              <Edit2 size={14} />
            </button>
            <button
              onClick={() => onDelete?.(source.id)}
              className="p-1.5 rounded hover:opacity-80 transition-opacity"
              style={{ color: 'var(--color-error)' }}
              title="Delete"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
