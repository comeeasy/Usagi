import { useRef, useEffect, useCallback } from 'react'
import cytoscape from 'cytoscape'
// @ts-ignore – cytoscape-dagre types not perfect
import dagre from 'cytoscape-dagre'

cytoscape.use(dagre)

export interface CyElement {
  data: {
    id: string
    label?: string
    kind?: string
    source?: string
    target?: string
    iri?: string
  }
  group?: 'nodes' | 'edges'
  classes?: string
}

interface GraphCanvasProps {
  elements?: CyElement[]
  layout?: string
  onNodeSelect?: (nodeId: string) => void
  onNodeDoubleClick?: (nodeId: string) => void
  cyRef?: React.MutableRefObject<cytoscape.Core | null>
}

export default function GraphCanvas({ elements = [], layout = 'dagre', onNodeSelect, onNodeDoubleClick, cyRef: externalCyRef }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const internalCyRef = useRef<cytoscape.Core | null>(null)
  const cyRef = externalCyRef ?? internalCyRef

  // Use refs for callbacks to avoid re-initializing cy on every render
  const onNodeSelectRef = useRef(onNodeSelect)
  const onNodeDoubleClickRef = useRef(onNodeDoubleClick)
  useEffect(() => { onNodeSelectRef.current = onNodeSelect }, [onNodeSelect])
  useEffect(() => { onNodeDoubleClickRef.current = onNodeDoubleClick }, [onNodeDoubleClick])

  const initCy = useCallback(() => {
    if (!containerRef.current) return

    if (cyRef.current) {
      cyRef.current.destroy()
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements: elements as cytoscape.ElementDefinition[],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#8B949E',
            'label': 'data(label)',
            'color': '#E6EDF3',
            'font-size': 11,
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 80,
            'height': 30,
            'shape': 'round-rectangle',
          },
        },
        {
          selector: 'node.concept',
          style: {
            'background-color': '#2F81F7',
            'label': 'data(label)',
            'color': '#E6EDF3',
            'font-size': 11,
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 80,
            'height': 30,
            'shape': 'round-rectangle',
            'text-wrap': 'wrap',
            'text-max-width': 70,
          },
        },
        {
          selector: 'node.individual',
          style: {
            'background-color': '#3FB950',
            'label': 'data(label)',
            'color': '#E6EDF3',
            'font-size': 10,
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 60,
            'height': 60,
            'shape': 'ellipse',
            'text-wrap': 'wrap',
            'text-max-width': 55,
          },
        },
        {
          selector: 'edge',
          style: {
            'line-color': '#30363D',
            'target-arrow-color': '#30363D',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 9,
            'color': '#8B949E',
            'text-rotation': 'autorotate',
            'width': 1.5,
          },
        },
        {
          selector: 'edge.object-property',
          style: {
            'line-color': '#A371F7',
            'target-arrow-color': '#A371F7',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 9,
            'color': '#8B949E',
            'text-rotation': 'autorotate',
            'width': 1.5,
          },
        },
        {
          selector: 'edge.subclass',
          style: {
            'line-color': '#30363D',
            'target-arrow-color': '#30363D',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 9,
            'color': '#8B949E',
            'text-rotation': 'autorotate',
            'width': 1.5,
            'line-style': 'dashed',
          },
        },
        {
          selector: ':selected',
          style: {
            'border-width': 2,
            'border-color': '#F0F6FC',
          },
        },
        {
          selector: 'node.expanded',
          style: {
            'border-width': 2,
            'border-color': '#F0A500',
            'border-style': 'solid',
          },
        },
      ],
      layout: {
        name: layout === 'dagre' ? 'dagre' : layout,
        rankDir: 'TB',
        nodeSep: 50,
        rankSep: 80,
      } as cytoscape.LayoutOptions,
      wheelSensitivity: 0.3,
    })

    cy.on('tap', 'node', (evt) => {
      onNodeSelectRef.current?.(evt.target.id())
    })

    cy.on('dbltap', 'node', (evt) => {
      onNodeDoubleClickRef.current?.(evt.target.id())
    })

    cy.one('layoutstop', () => { cy.fit(undefined, 40) })

    cyRef.current = cy
  }, [elements, layout])

  useEffect(() => {
    initCy()
    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [initCy])

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ minHeight: 400, backgroundColor: 'var(--color-bg-base)' }}
    />
  )
}
