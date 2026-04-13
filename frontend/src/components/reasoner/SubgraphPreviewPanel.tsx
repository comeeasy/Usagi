/**
 * SubgraphPreviewPanel — 선택한 entity/relation 기반 서브그래프 실시간 미리보기
 *
 * - selectedEntities/selectedRelations 변경 후 500ms debounce → getSubgraph() 호출
 * - GraphCanvas 로 렌더링 (read-only)
 * - 노드 클릭 → onAddEntity(iri) 로 seed entity 추가
 */
import { useEffect, useRef, useState } from 'react'
import { Network } from 'lucide-react'
import GraphCanvas from '@/components/graph/GraphCanvas'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { getSubgraph } from '@/api/ontologies'
import type { SubgraphData } from '@/api/ontologies'

interface SubgraphPreviewPanelProps {
  ontologyId: string
  dataset?: string
  selectedEntities: string[]
  selectedRelations: string[]
  onAddEntity: (iri: string) => void
}

export default function SubgraphPreviewPanel({
  ontologyId,
  dataset,
  selectedEntities,
  selectedRelations,
  onAddEntity,
}: SubgraphPreviewPanelProps) {
  const [data, setData]       = useState<SubgraphData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)

    if (selectedEntities.length === 0) {
      setData(null)
      setLoading(false)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    timerRef.current = setTimeout(() => {
      getSubgraph(ontologyId, {
        rootIris:      selectedEntities,
        relationIris:  selectedRelations.length > 0 ? selectedRelations : undefined,
        dataset,
      })
        .then((res) => {
          setData(res)
          setLoading(false)
        })
        .catch(() => {
          setError('Failed to load subgraph')
          setLoading(false)
        })
    }, 500)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [ontologyId, dataset, selectedEntities.join(','), selectedRelations.join(',')])  // eslint-disable-line react-hooks/exhaustive-deps

  const nodeCount = data?.nodes.length ?? 0
  const edgeCount = data?.edges.length ?? 0

  return (
    <div className="flex flex-col h-full relative">
      {/* Header stats */}
      {data && !loading && (
        <div
          className="flex items-center gap-2 px-3 py-1.5 border-b text-xs"
          style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
        >
          <Network size={11} />
          <span>{nodeCount} nodes · {edgeCount} edges</span>
        </div>
      )}

      {/* Empty state */}
      {selectedEntities.length === 0 && (
        <div
          className="flex flex-col items-center justify-center h-full gap-3"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <Network size={40} style={{ opacity: 0.25 }} />
          <p className="text-sm">Select seed entities to preview the subgraph</p>
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: 'var(--color-text-muted)' }}>
          <LoadingSpinner size="md" />
          <p className="text-xs">Building subgraph…</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-center justify-center h-full">
          <p className="text-xs" style={{ color: 'var(--color-error)' }}>{error}</p>
        </div>
      )}

      {/* Graph */}
      {!loading && !error && data && data.nodes.length > 0 && (
        <div className="flex-1 min-h-0">
          <GraphCanvas
            elements={[...data.nodes, ...data.edges]}
            layout="dagre"
            onNodeDoubleClick={(nodeId) => onAddEntity(nodeId)}
          />
        </div>
      )}

      {/* No results */}
      {!loading && !error && data && data.nodes.length === 0 && (
        <div
          className="flex flex-col items-center justify-center h-full gap-2"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <Network size={40} style={{ opacity: 0.25 }} />
          <p className="text-sm">No connected subgraph found</p>
          <p className="text-xs">Try adding more seed entities</p>
        </div>
      )}
    </div>
  )
}
