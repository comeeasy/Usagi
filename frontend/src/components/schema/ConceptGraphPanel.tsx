/**
 * ConceptGraphPanel — Schema 탭 하단 그래프 (Concept 노드만 표시)
 *
 * 선택된 Concept IRI 기준으로 subgraph를 조회하되,
 * individual 노드는 필터링하여 Class 구조만 시각화한다.
 */
import { useEffect, useState, useCallback } from 'react'
import { getSubgraph } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import GraphCanvas, { type CyElement } from '@/components/graph/GraphCanvas'
import LoadingSpinner from '@/components/shared/LoadingSpinner'

interface Props {
  ontologyId: string
  conceptIris: string[]
}

function filterConceptsOnly(elements: CyElement[]): CyElement[] {
  // individual 노드 제거, 해당 노드에 연결된 엣지도 제거
  const individualIds = new Set(
    elements
      .filter((e) => !e.data.source && e.data.kind === 'individual')
      .map((e) => e.data.id),
  )
  return elements.filter((e) => {
    if (individualIds.has(e.data.id)) return false
    if (e.data.source && (individualIds.has(e.data.source) || (e.data.target != null && individualIds.has(e.data.target)))) return false
    return true
  })
}

export default function ConceptGraphPanel({ ontologyId, conceptIris }: Props) {
  const { dataset } = useDataset()
  const [elements, setElements] = useState<CyElement[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedIris, setExpandedIris] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (conceptIris.length === 0) {
      setElements([])
      setExpandedIris(new Set())
      return
    }
    setLoading(true)
    getSubgraph(ontologyId, { rootIris: conceptIris, depth: 2, dataset })
      .then((data) => {
        setElements(filterConceptsOnly([...data.nodes, ...data.edges]))
        setExpandedIris(new Set())
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ontologyId, conceptIris.join(','), dataset]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleNodeDoubleClick = useCallback(async (iri: string) => {
    if (expandedIris.has(iri)) return
    setExpandedIris((prev) => new Set([...prev, iri]))
    try {
      const data = await getSubgraph(ontologyId, { rootIris: [iri], depth: 1, dataset })
      const newElems = filterConceptsOnly([...data.nodes, ...data.edges])
      setElements((prev) => {
        const existingIds = new Set(prev.map((e) => e.data.id))
        const toAdd = newElems.filter((e) => !existingIds.has(e.data.id))
        return toAdd.length > 0 ? [...prev, ...toAdd] : prev
      })
    } catch {
      setExpandedIris((prev) => { const s = new Set(prev); s.delete(iri); return s })
    }
  }, [ontologyId, dataset, expandedIris])

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* Placeholder when no concept selected */}
      {conceptIris.length === 0 && (
        <div
          className="absolute inset-0 flex items-center justify-center text-sm"
          style={{ color: 'var(--color-text-muted)', zIndex: 1 }}
        >
          Select a concept to visualize class hierarchy
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10"
          style={{ backgroundColor: 'rgba(0,0,0,0.15)' }}>
          <LoadingSpinner size="sm" />
        </div>
      )}

      <GraphCanvas
        elements={elements}
        onNodeDoubleClick={handleNodeDoubleClick}
      />
    </div>
  )
}
