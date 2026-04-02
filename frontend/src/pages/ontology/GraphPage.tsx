import { useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { deleteConcept, deleteIndividual } from '@/api/entities'
import { X, Search } from 'lucide-react'
import cytoscape from 'cytoscape'
import OntologyTabs from '@/components/layout/OntologyTabs'
import GraphCanvas from '@/components/graph/GraphCanvas'
import GraphControls from '@/components/graph/GraphControls'
import GraphLegend from '@/components/graph/GraphLegend'
import NodeDetailPanel from '@/components/graph/NodeDetailPanel'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useSubgraph } from '@/hooks/useSubgraph'
import { useEntitySearch } from '@/hooks/useEntitySearch'
import type { CyElement } from '@/components/graph/GraphCanvas'
import type { Concept } from '@/types/concept'
import type { Individual } from '@/types/individual'

type SearchResult = Concept | Individual

export default function GraphPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const navigate = useNavigate()
  const cyRef = useRef<cytoscape.Core | null>(null)

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [layout, setLayout] = useState('dagre')
  const [elements, setElements] = useState<CyElement[]>([])
  const [hasLoaded, setHasLoaded] = useState(false)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [useVector, setUseVector] = useState(false)
  const [rootEntities, setRootEntities] = useState<SearchResult[]>([])
  const [depth, setDepth] = useState(2)

  const searchResults = useEntitySearch(ontologyId, searchQuery, 'all', useVector)
  const subgraphMutation = useSubgraph(ontologyId)

  const deleteConceptMutation = useMutation({
    mutationFn: (iri: string) => deleteConcept(ontologyId!, iri),
    onSuccess: (_, iri) => {
      setElements((prev) => prev.filter((el) => el.data.id !== iri && el.data.source !== iri && el.data.target !== iri))
      setRootEntities((prev) => prev.filter((e) => e.iri !== iri))
      setSelectedNodeId(null)
    },
  })

  const deleteIndividualMutation = useMutation({
    mutationFn: (iri: string) => deleteIndividual(ontologyId!, iri),
    onSuccess: (_, iri) => {
      setElements((prev) => prev.filter((el) => el.data.id !== iri && el.data.source !== iri && el.data.target !== iri))
      setRootEntities((prev) => prev.filter((e) => e.iri !== iri))
      setSelectedNodeId(null)
    },
  })

  const loadGraph = async (iris: string[], d: number) => {
    const result = await subgraphMutation.mutateAsync({ rootIris: iris.length > 0 ? iris : undefined, depth: d })
    const cyElements: CyElement[] = [
      ...result.nodes.map((n) => ({ group: 'nodes' as const, data: n.data as CyElement['data'], classes: n.classes })),
      ...result.edges.map((e) => ({ group: 'edges' as const, data: e.data as CyElement['data'], classes: e.classes })),
    ]
    setElements(cyElements)
    setHasLoaded(true)
  }

  const handleSelectEntity = (entity: SearchResult) => {
    if (rootEntities.find((e) => e.iri === entity.iri)) return
    const next = [...rootEntities, entity]
    setRootEntities(next)
    setSearchQuery('')
    setShowDropdown(false)
    loadGraph(next.map((e) => e.iri), depth)
  }

  const handleRemoveRoot = (iri: string) => {
    const next = rootEntities.filter((e) => e.iri !== iri)
    setRootEntities(next)
    if (next.length === 0) {
      setElements([])
      setHasLoaded(false)
    } else {
      loadGraph(next.map((e) => e.iri), depth)
    }
  }

  const handleDepthChange = (d: number) => {
    setDepth(d)
    if (hasLoaded) loadGraph(rootEntities.map((e) => e.iri), d)
  }

  const handleLoadAll = () => {
    setRootEntities([])
    loadGraph([], depth)
  }

  const handleLayoutChange = (newLayout: string) => {
    setLayout(newLayout)
    if (cyRef.current) {
      cyRef.current.layout({ name: newLayout === 'dagre' ? 'dagre' : newLayout } as cytoscape.LayoutOptions).run()
    }
  }

  const selectedNodeEl = selectedNodeId ? cyRef.current?.getElementById(selectedNodeId) : undefined
  const selectedNodeData = (selectedNodeEl && selectedNodeEl.length > 0) ? selectedNodeEl.data() : null
  const dropdownItems = searchResults.data?.filter((r) => !rootEntities.find((e) => e.iri === r.iri)) ?? []

  return (
    <div className="flex flex-col h-full">
      <OntologyTabs />

      <div className="flex flex-1 overflow-hidden">
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
          </div>

          {/* Search + depth row */}
          <div className="flex items-start gap-3 flex-wrap">
            {/* Entity search */}
            <div className="relative flex-1 min-w-64">
              <div
                className="flex items-center gap-2 px-3 py-2 rounded-lg border"
                style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
              >
                <Search size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => { setSearchQuery(e.target.value); setShowDropdown(true) }}
                  onFocus={() => { if (searchQuery) setShowDropdown(true) }}
                  onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                  placeholder="Search entities to explore..."
                  className="flex-1 text-sm bg-transparent outline-none"
                  style={{ color: 'var(--color-text-primary)' }}
                />
                {searchResults.isFetching && <LoadingSpinner size="sm" />}
                <label className="flex items-center gap-1 text-xs cursor-pointer select-none flex-shrink-0">
                  <div
                    className="w-7 h-3.5 rounded-full relative"
                    style={{ backgroundColor: useVector ? 'var(--color-primary)' : 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}
                    onClick={() => setUseVector((v) => !v)}
                  >
                    <div
                      className="absolute top-px w-2.5 h-2.5 rounded-full transition-transform"
                      style={{ backgroundColor: 'var(--color-text-primary)', transform: useVector ? 'translateX(14px)' : 'translateX(1px)' }}
                    />
                  </div>
                  <span style={{ color: 'var(--color-text-muted)' }}>Vector</span>
                </label>
              </div>

              {/* Dropdown */}
              {showDropdown && dropdownItems.length > 0 && (
                <div
                  className="absolute top-full left-0 right-0 z-50 mt-1 rounded-lg border overflow-hidden shadow-lg"
                  style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
                >
                  {dropdownItems.slice(0, 8).map((entity) => (
                    <button
                      key={entity.iri}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left hover:opacity-80 text-sm"
                      style={{ borderBottom: '1px solid var(--color-border)' }}
                      onMouseDown={() => handleSelectEntity(entity)}
                    >
                      <span
                        className="text-xs px-1.5 py-0.5 rounded flex-shrink-0"
                        style={{
                          backgroundColor: 'super_classes' in entity ? 'rgba(47,129,247,0.15)' : 'rgba(63,185,80,0.15)',
                          color: 'super_classes' in entity ? 'var(--color-primary)' : 'var(--color-success)',
                        }}
                      >
                        {'super_classes' in entity ? 'C' : 'I'}
                      </span>
                      <span style={{ color: 'var(--color-text-primary)' }}>{entity.label || entity.iri}</span>
                      <span className="text-xs truncate" style={{ color: 'var(--color-text-muted)' }}>{entity.iri}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Depth selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Depth</span>
              <div className="flex gap-1">
                {[1, 2, 3].map((d) => (
                  <button
                    key={d}
                    onClick={() => handleDepthChange(d)}
                    className="w-7 h-7 rounded text-xs font-medium"
                    style={{
                      backgroundColor: depth === d ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                      color: depth === d ? '#fff' : 'var(--color-text-secondary)',
                      border: '1px solid var(--color-border)',
                    }}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            {/* Load all link */}
            <button
              onClick={handleLoadAll}
              disabled={subgraphMutation.isPending}
              className="text-xs hover:opacity-80 disabled:opacity-50"
              style={{ color: 'var(--color-text-muted)', textDecoration: 'underline' }}
            >
              Load entire ontology
            </button>
          </div>

          {/* Root entity chips */}
          {rootEntities.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {rootEntities.map((e) => (
                <div
                  key={e.iri}
                  className="flex items-center gap-1 px-2 py-1 rounded-full text-xs"
                  style={{ backgroundColor: 'rgba(47,129,247,0.15)', border: '1px solid rgba(47,129,247,0.3)' }}
                >
                  <span style={{ color: 'var(--color-primary)' }}>{e.label || e.iri}</span>
                  <button onClick={() => handleRemoveRoot(e.iri)} style={{ color: 'var(--color-primary)' }}>
                    <X size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {subgraphMutation.error && (
            <div
              className="p-3 rounded-lg border text-sm"
              style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)' }}
            >
              Failed to load graph: {subgraphMutation.error.message}
            </div>
          )}

          {/* Empty state */}
          {!hasLoaded && !subgraphMutation.isPending && (
            <div
              className="flex flex-col items-center justify-center flex-1 rounded-lg border border-dashed gap-2"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
            >
              <Search size={24} />
              <p className="text-sm">Search for an entity to explore its graph</p>
              <button onClick={handleLoadAll} className="text-xs hover:opacity-80" style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>
                or load entire ontology
              </button>
            </div>
          )}

          {/* Canvas */}
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
                onNodeSelect={setSelectedNodeId}
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
            nodeData={selectedNodeData}
            onClose={() => setSelectedNodeId(null)}
            onEdit={() => navigate(`/${ontologyId}/entities`, {
              state: { editIri: selectedNodeData?.iri, entityType: selectedNodeData?.kind },
            })}
            onDelete={() => {
              if (!selectedNodeData || !window.confirm(`Delete "${selectedNodeData.label || selectedNodeData.iri}"?`)) return
              if (selectedNodeData.kind === 'concept') {
                deleteConceptMutation.mutate(selectedNodeData.iri as string)
              } else {
                deleteIndividualMutation.mutate(selectedNodeData.iri as string)
              }
            }}
          />
        )}
      </div>
    </div>
  )
}
