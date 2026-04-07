import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { getSubgraph } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import GraphCanvas, { type CyElement } from './GraphCanvas'
import LoadingSpinner from '@/components/shared/LoadingSpinner'

interface EntityGraphPanelProps {
  ontologyId: string
  entityIris: string[]
  onRemoveIri: (iri: string) => void
}

function shortLabel(iri: string) {
  if (iri.includes('#')) return iri.split('#').at(-1) ?? iri
  return iri.split('/').at(-1) ?? iri
}

export default function EntityGraphPanel({ ontologyId, entityIris, onRemoveIri }: EntityGraphPanelProps) {
  const { dataset } = useDataset()
  const [elements, setElements] = useState<CyElement[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (entityIris.length === 0) {
      setElements([])
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    getSubgraph(ontologyId, { rootIris: entityIris, depth: 2, dataset })
      .then((data) => setElements([...data.nodes, ...data.edges]))
      .catch(() => setError('Failed to load graph'))
      .finally(() => setLoading(false))
  }, [ontologyId, entityIris.join(','), dataset]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Chips */}
      {entityIris.length > 0 && (
        <div className="flex flex-wrap gap-1 px-2 py-1.5 flex-shrink-0"
             style={{ borderBottom: '1px solid var(--color-border)' }}>
          {entityIris.map((iri) => (
            <span key={iri}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs"
              style={{ background: 'var(--color-primary)', color: '#fff' }}
              title={iri}
            >
              {shortLabel(iri)}
              <button onClick={() => onRemoveIri(iri)} className="hover:opacity-70 leading-none">
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Canvas area */}
      <div className="flex-1 overflow-hidden relative">
        {entityIris.length === 0 && (
          <div className="flex items-center justify-center h-full text-sm"
               style={{ color: 'var(--color-text-muted)' }}>
            Select an entity to view graph
          </div>
        )}

        {entityIris.length > 0 && loading && (
          <div className="flex items-center justify-center h-full">
            <LoadingSpinner />
          </div>
        )}

        {entityIris.length > 0 && !loading && error && (
          <div className="flex items-center justify-center h-full text-sm text-red-500">
            {error}
          </div>
        )}

        {entityIris.length > 0 && !loading && !error && (
          <GraphCanvas elements={elements} layout="dagre" />
        )}
      </div>
    </div>
  )
}
