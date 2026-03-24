import type { ProvenanceRecord } from '@/types/individual'
import IRIBadge from '@/components/shared/IRIBadge'
import { Database, Clock, Link } from 'lucide-react'

interface ProvenancePanelProps {
  records?: ProvenanceRecord[]
}

const SOURCE_TYPE_COLORS: Record<string, string> = {
  jdbc: '#2F81F7',
  api: '#3FB950',
  stream: '#D29922',
  file: '#79C0FF',
}

export default function ProvenancePanel({ records = [] }: ProvenancePanelProps) {
  return (
    <section>
      <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-secondary)' }}>
        Provenance
      </h3>

      {records.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          No provenance records
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {records.map((r, i) => (
            <div
              key={i}
              className="p-3 rounded-lg border"
              style={{
                backgroundColor: 'var(--color-bg-elevated)',
                borderColor: 'var(--color-border)',
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Database size={12} style={{ color: SOURCE_TYPE_COLORS[r.source_type] ?? 'var(--color-text-muted)' }} />
                <span
                  className="text-xs font-semibold px-1.5 py-0.5 rounded uppercase"
                  style={{
                    backgroundColor: `${SOURCE_TYPE_COLORS[r.source_type] ?? '#8B949E'}20`,
                    color: SOURCE_TYPE_COLORS[r.source_type] ?? 'var(--color-text-muted)',
                  }}
                >
                  {r.source_type}
                </span>
                <span className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>
                  {r.source_id}
                </span>
              </div>

              <div className="flex flex-col gap-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                <div className="flex items-center gap-1.5">
                  <Clock size={10} />
                  <span>Generated: {new Date(r.generated_at).toLocaleString()}</span>
                </div>

                {r.record_id && (
                  <div className="flex items-center gap-1.5">
                    <Link size={10} />
                    <span>Record ID: {r.record_id}</span>
                  </div>
                )}

                {r.named_graph_iri && (
                  <div className="flex items-center gap-1.5">
                    <span>Graph:</span>
                    <IRIBadge iri={r.named_graph_iri} />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
