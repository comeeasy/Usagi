import { useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import cytoscape from 'cytoscape'
import OntologyTabs from '@/components/layout/OntologyTabs'
import GraphCanvas from '@/components/graph/GraphCanvas'
import GraphControls from '@/components/graph/GraphControls'
import GraphLegend from '@/components/graph/GraphLegend'
import NodeDetailPanel from '@/components/graph/NodeDetailPanel'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useSubgraph } from '@/hooks/useSubgraph'
import type { CyElement } from '@/components/graph/GraphCanvas'

export default function GraphPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [layout, setLayout] = useState('dagre')
  const [elements, setElements] = useState<CyElement[]>([])
  const [hasLoaded, setHasLoaded] = useState(false)

  const subgraphMutation = useSubgraph(ontologyId)

  const loadGraph = async () => {
    const result = await subgraphMutation.mutateAsync({ depth: 3, includeIndividuals: true })
    const cyElements: CyElement[] = [
      ...result.nodes.map((n) => ({ group: 'nodes' as const, data: n.data as CyElement['data'] })),
      ...result.edges.map((e) => ({ group: 'edges' as const, data: e.data as CyElement['data'] })),
    ]
    setElements(cyElements)
    setHasLoaded(true)
  }

  const selectedNode = cyRef.current?.getElementById(selectedNodeId ?? '')

  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId)
  }

  const handleLayoutChange = (newLayout: string) => {
    setLayout(newLayout)
    if (cyRef.current) {
      cyRef.current.layout({ name: newLayout === 'dagre' ? 'dagre' : newLayout } as cytoscape.LayoutOptions).run()
    }
  }

  return (
    <div className="flex flex-col h-full">
      <OntologyTabs />

      <div className="flex flex-1 overflow-hidden">
        {/* Main graph area */}
        <div className="flex flex-col flex-1 overflow-hidden p-4 gap-3">
          {/* Controls row */}
          <div className="flex items-center gap-3 flex-wrap">
            <GraphControls
              currentLayout={layout}
              onLayoutChange={handleLayoutChange}
              onZoomIn={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
              onZoomOut={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
              onFit={() => cyRef.current?.fit()}
            />

            {!hasLoaded && (
              <button
                onClick={loadGraph}
                disabled={subgraphMutation.isPending}
                className="flex items-center gap-2 px-3 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
                style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              >
                {subgraphMutation.isPending && <LoadingSpinner size="sm" />}
                {subgraphMutation.isPending ? 'Loading...' : 'Load Graph'}
              </button>
            )}

            {hasLoaded && (
              <button
                onClick={loadGraph}
                disabled={subgraphMutation.isPending}
                className="flex items-center gap-2 px-3 py-2 rounded text-sm hover:opacity-80 disabled:opacity-50"
                style={{
                  backgroundColor: 'var(--color-bg-elevated)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                {subgraphMutation.isPending && <LoadingSpinner size="sm" />}
                Refresh
              </button>
            )}
          </div>

          {subgraphMutation.error && (
            <div
              className="p-3 rounded-lg border text-sm"
              style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)' }}
            >
              Failed to load graph: {subgraphMutation.error.message}
            </div>
          )}

          {!hasLoaded && !subgraphMutation.isPending && (
            <div
              className="flex flex-col items-center justify-center flex-1 rounded-lg border border-dashed gap-4"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
            >
              <p>Click "Load Graph" to visualize the ontology</p>
            </div>
          )}

          {(hasLoaded || subgraphMutation.isPending) && (
            <div className="flex-1 relative overflow-hidden rounded-lg border" style={{ borderColor: 'var(--color-border)' }}>
              {subgraphMutation.isPending && (
                <div className="absolute inset-0 flex items-center justify-center z-10" style={{ backgroundColor: 'rgba(0,0,0,0.4)' }}>
                  <LoadingSpinner size="lg" />
                </div>
              )}
              <GraphCanvas
                elements={elements}
                layout={layout}
                onNodeSelect={handleNodeSelect}
                cyRef={cyRef}
              />
            </div>
          )}
        </div>

        {/* Legend */}
        <div className="w-40 p-3 border-l flex-shrink-0" style={{ borderColor: 'var(--color-border)' }}>
          <GraphLegend />
        </div>

        {/* Node detail panel */}
        {selectedNodeId && (
          <NodeDetailPanel
            nodeId={selectedNodeId}
            nodeData={selectedNode?.data() ?? null}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </div>
    </div>
  )
}
