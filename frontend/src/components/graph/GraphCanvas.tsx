import { useRef, useEffect, useCallback } from 'react'
import cytoscape from 'cytoscape'
// @ts-ignore – cytoscape-dagre types not perfect
import dagre from 'cytoscape-dagre'

cytoscape.use(dagre)

export interface CyElement {
  data: {
    id: string
    label?: string
    type?: 'concept' | 'individual'
    source?: string
    target?: string
    iri?: string
  }
  group?: 'nodes' | 'edges'
}

interface GraphCanvasProps {
  elements?: CyElement[]
  layout?: string
  onNodeSelect?: (nodeId: string) => void
  cyRef?: React.MutableRefObject<cytoscape.Core | null>
}

export default function GraphCanvas({ elements = [], layout = 'dagre', onNodeSelect, cyRef: externalCyRef }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const internalCyRef = useRef<cytoscape.Core | null>(null)
  const cyRef = externalCyRef ?? internalCyRef

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
          selector: 'node[type = "concept"]',
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
          selector: 'node[type = "individual"]',
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
          selector: 'edge[type = "object"]',
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
          selector: 'edge[type = "subclass"]',
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
          selector: ':selected',
          style: {
            'border-width': 2,
            'border-color': '#F0F6FC',
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
      onNodeSelect?.(evt.target.id())
    })

    cyRef.current = cy
  }, [elements, layout, onNodeSelect])

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
