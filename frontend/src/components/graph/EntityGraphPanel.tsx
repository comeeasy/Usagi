import { useEffect, useState, useCallback } from 'react'
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

function isBlankNodeIri(iri: string): boolean {
  return iri.startsWith('_:')
}

function isRestrictionEdgeId(edgeId: string): boolean {
  return (
    edgeId.includes('owl#someValuesFrom') ||
    edgeId.includes('owl#allValuesFrom') ||
    edgeId.includes('owl#hasValue') ||
    edgeId.includes('owl#onProperty') ||
    edgeId.includes('owl#minCardinality') ||
    edgeId.includes('owl#maxCardinality') ||
    edgeId.includes('owl#qualifiedCardinality') ||
    edgeId.includes('owl#cardinality')
  )
}

export default function EntityGraphPanel({ ontologyId, entityIris, onRemoveIri }: EntityGraphPanelProps) {
  const { dataset } = useDataset()
  const [elements, setElements] = useState<CyElement[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedIris, setExpandedIris] = useState<Set<string>>(new Set())

  // 초기 로드: entityIris 변경 시 전체 재조회
  useEffect(() => {
    if (entityIris.length === 0) {
      setElements([])
      setExpandedIris(new Set())
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    getSubgraph(ontologyId, { rootIris: entityIris, depth: 1, dataset })
      .then((data) => {
        const allowedNodeIds = new Set(
          data.nodes
            .map((n) => n.data.id)
            .filter((id) => !isBlankNodeIri(id)),
        )

        const normalizedNodes = data.nodes
          .filter((n) => allowedNodeIds.has(n.data.id))
          .map((n) => ({
            ...n,
            data: {
              ...n.data,
              // Avoid raw full IRI labels in graph UI.
              label: n.data.label.includes('://') ? shortLabel(n.data.iri) : n.data.label,
            },
          }))

        const normalizedEdges = data.edges.filter(
          (e) =>
            allowedNodeIds.has(e.data.source) &&
            allowedNodeIds.has(e.data.target) &&
            !isRestrictionEdgeId(e.data.id),
        )

        setElements([...normalizedNodes, ...normalizedEdges])
        setExpandedIris(new Set())
      })
      .catch(() => setError('Failed to load graph'))
      .finally(() => setLoading(false))
  }, [ontologyId, entityIris.join(','), dataset]) // eslint-disable-line react-hooks/exhaustive-deps

  // 더블클릭: 해당 노드를 depth=1 로 확장
  const handleNodeDoubleClick = useCallback(async (iri: string) => {
    if (expandedIris.has(iri)) return
    setExpandedIris((prev) => new Set([...prev, iri]))
    try {
      const data = await getSubgraph(ontologyId, { rootIris: [iri], depth: 1, dataset })
      const allowedNodeIds = new Set(
        data.nodes
          .map((n) => n.data.id)
          .filter((id) => !isBlankNodeIri(id)),
      )
      const newElems = [
        ...data.nodes
          .filter((n) => allowedNodeIds.has(n.data.id))
          .map((n) => ({
            ...n,
            data: {
              ...n.data,
              label: n.data.label.includes('://') ? shortLabel(n.data.iri) : n.data.label,
            },
          })),
        ...data.edges.filter(
          (e) =>
            allowedNodeIds.has(e.data.source) &&
            allowedNodeIds.has(e.data.target) &&
            !isRestrictionEdgeId(e.data.id),
        ),
      ]
      setElements((prev) => {
        const existingIds = new Set(prev.map((e) => e.data.id))
        const toAdd = newElems.filter((e) => !existingIds.has(e.data.id))
        return toAdd.length > 0 ? [...prev, ...toAdd] : prev
      })
    } catch {
      setExpandedIris((prev) => { const s = new Set(prev); s.delete(iri); return s })
    }
  }, [ontologyId, dataset, expandedIris])

  // expanded 클래스 마킹
  const displayElements = elements.map((e) =>
    expandedIris.has(e.data.id)
      ? { ...e, classes: ((e.classes ?? '') + ' expanded').trim() }
      : e,
  )

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
          <GraphCanvas
            elements={displayElements}
            layout="dagre"
            onNodeDoubleClick={handleNodeDoubleClick}
          />
        )}
      </div>
    </div>
  )
}
