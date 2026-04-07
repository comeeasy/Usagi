import { useQuery } from '@tanstack/react-query'
import { Upload } from 'lucide-react'
import { listNamedGraphs } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { NamedGraph } from '@/api/ontologies'

const SOURCE_TYPE_LABEL: Record<string, string> = {
  file: 'File',
  url: 'URL',
  standard: 'Standard',
  manual: 'Manual',
}

const SOURCE_TYPE_COLOR: Record<string, string> = {
  file: '#6366f1',
  url: '#0ea5e9',
  standard: '#10b981',
  manual: '#f59e0b',
}

interface NamedGraphListProps {
  ontologyId: string
  onImportClick: () => void
}

export default function NamedGraphList({ ontologyId, onImportClick }: NamedGraphListProps) {
  const { dataset } = useDataset()

  const query = useQuery({
    queryKey: ['named-graphs', ontologyId, dataset],
    queryFn: () => listNamedGraphs(ontologyId, dataset),
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3"
           style={{ borderBottom: '1px solid var(--color-border)' }}>
        <h2 className="text-sm font-semibold">Named Graphs</h2>
        <button
          onClick={onImportClick}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium hover:opacity-80"
          style={{ background: 'var(--color-primary)', color: '#fff' }}
        >
          <Upload size={14} />
          Import
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {query.isPending && (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        )}

        {query.isSuccess && query.data.length === 0 && (
          <div className="text-center py-8 text-sm" style={{ color: 'var(--color-text-muted)' }}>
            No graphs — use Import to load ontology data
          </div>
        )}

        {query.isSuccess && query.data.length > 0 && (
          <div className="flex flex-col gap-2">
            {query.data.map((g: NamedGraph) => (
              <GraphCard key={g.iri} graph={g} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function GraphCard({ graph }: { graph: NamedGraph }) {
  const sourceType = graph.source_type ?? 'manual'
  const typeLabel = SOURCE_TYPE_LABEL[sourceType] ?? sourceType
  const typeColor = SOURCE_TYPE_COLOR[sourceType] ?? '#94a3b8'

  return (
    <div className="rounded-lg p-3 text-sm"
         style={{ border: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-mono text-xs break-all" style={{ color: 'var(--color-text)' }}>
          {graph.iri}
        </span>
        <span className="shrink-0 text-xs px-1.5 py-0.5 rounded font-medium"
              style={{ background: `${typeColor}20`, color: typeColor }}>
          {typeLabel}
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
        <span>{graph.triple_count.toLocaleString()} triples</span>
        {graph.source_label && (
          <span className="truncate max-w-xs" title={graph.source_label}>
            {graph.source_label}
          </span>
        )}
      </div>
    </div>
  )
}
