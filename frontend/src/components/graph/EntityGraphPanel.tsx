import { useEffect, useState } from 'react'
import { getSubgraph } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import GraphCanvas, { type CyElement } from './GraphCanvas'
import LoadingSpinner from '@/components/shared/LoadingSpinner'

interface EntityGraphPanelProps {
  ontologyId: string
  entityIri: string | null
}

export default function EntityGraphPanel({ ontologyId, entityIri }: EntityGraphPanelProps) {
  const { dataset } = useDataset()
  const [elements, setElements] = useState<CyElement[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!entityIri) {
      setElements([])
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    getSubgraph(ontologyId, { rootIris: [entityIri], depth: 2, dataset })
      .then((data) => {
        setElements([...data.nodes, ...data.edges])
      })
      .catch(() => setError('Failed to load graph'))
      .finally(() => setLoading(false))
  }, [ontologyId, entityIri, dataset])

  if (!entityIri) {
    return (
      <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Select an entity to view graph
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-red-500">
        {error}
      </div>
    )
  }

  return (
    <div className="h-full w-full">
      <GraphCanvas elements={elements} layout="dagre" />
    </div>
  )
}
