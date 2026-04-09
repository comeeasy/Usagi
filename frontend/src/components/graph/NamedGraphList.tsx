import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Upload, Pencil } from 'lucide-react'
import { listNamedGraphs } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import TtlEditorPanel from '@/components/graph/TtlEditorPanel'
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
  const { selectedGraphIris, setKnownGraphs, toggleGraph, selectAll, deselectAll } = useNamedGraphs()
  const [editingIri, setEditingIri] = useState<string | null>(null)

  const query = useQuery({
    queryKey: ['named-graphs', ontologyId, dataset],
    queryFn: () => listNamedGraphs(ontologyId, dataset),
  })

  // 그래프 목록이 로드되면 Context에 알림
  useEffect(() => {
    if (query.data) {
      setKnownGraphs(query.data.map((g) => g.iri))
    }
  }, [query.data, setKnownGraphs])

  const allCount = query.data?.length ?? 0
  const selectedCount = selectedGraphIris.length
  const allSelected = allCount > 0 && selectedCount === allCount

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
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

      {/* Select all / none bar */}
      {allCount > 0 && (
        <div
          className="flex items-center gap-3 px-4 py-2 text-xs"
          style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}
        >
          <span>
            {selectedCount}/{allCount} selected
          </span>
          <button
            onClick={allSelected ? deselectAll : selectAll}
            className="underline hover:opacity-70"
            style={{ color: 'var(--color-primary)' }}
          >
            {allSelected ? 'Deselect all' : 'Select all'}
          </button>
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {query.isPending && (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        )}

        {query.isSuccess && query.data.length === 0 && (
          <div
            className="text-center py-8 text-sm"
            style={{ color: 'var(--color-text-muted)' }}
          >
            No graphs — use Import to load ontology data
          </div>
        )}

        {query.isSuccess && query.data.length > 0 && (
          <div className="flex flex-col gap-2">
            {query.data.map((g: NamedGraph) => (
              <div key={g.iri} className="flex flex-col gap-1">
                <GraphCard
                  graph={g}
                  checked={selectedGraphIris.includes(g.iri)}
                  onToggle={() => toggleGraph(g.iri)}
                  onEdit={() => setEditingIri(editingIri === g.iri ? null : g.iri)}
                  editing={editingIri === g.iri}
                />
                {editingIri === g.iri && (
                  <TtlEditorPanel
                    ontologyId={ontologyId}
                    graphIri={g.iri}
                    onClose={() => setEditingIri(null)}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function GraphCard({
  graph,
  checked,
  onToggle,
  onEdit,
  editing,
}: {
  graph: NamedGraph
  checked: boolean
  onToggle: () => void
  onEdit: () => void
  editing: boolean
}) {
  const sourceType = graph.source_type ?? 'manual'
  const typeLabel = SOURCE_TYPE_LABEL[sourceType] ?? sourceType
  const typeColor = SOURCE_TYPE_COLOR[sourceType] ?? '#94a3b8'

  return (
    <div
      className="rounded-lg p-3 text-sm cursor-pointer"
      style={{
        border: `1px solid ${checked ? 'var(--color-primary)' : 'var(--color-border)'}`,
        background: checked ? 'var(--color-bg-elevated)' : 'var(--color-surface)',
        opacity: checked ? 1 : 0.6,
      }}
      onClick={onToggle}
    >
      <div className="flex items-start gap-2 mb-2">
        <input
          type="checkbox"
          checked={checked}
          readOnly
          onClick={(e) => {
            e.stopPropagation()
            onToggle()
          }}
          className="mt-0.5 w-3.5 h-3.5 flex-shrink-0"
          style={{ accentColor: 'var(--color-primary)' }}
        />
        <span className="font-mono text-xs break-all flex-1" style={{ color: 'var(--color-text)' }}>
          {graph.iri}
        </span>
        <span
          className="shrink-0 text-xs px-1.5 py-0.5 rounded font-medium"
          style={{ background: `${typeColor}20`, color: typeColor }}
        >
          {typeLabel}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onEdit() }}
          className="shrink-0 p-1 rounded hover:opacity-80"
          title="Edit TTL"
          style={{
            color: editing ? 'var(--color-primary)' : 'var(--color-text-muted)',
            background: editing ? 'var(--color-primary)18' : 'transparent',
          }}
        >
          <Pencil size={12} />
        </button>
      </div>

      <div className="flex items-center gap-4 text-xs pl-5" style={{ color: 'var(--color-text-muted)' }}>
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
