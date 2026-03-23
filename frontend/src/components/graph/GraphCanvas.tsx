// TODO: Cytoscape.js 래퍼, cy 인스턴스 useRef 관리
// cytoscape-dagre 레이아웃 지원
// 노드 클릭 → onNodeSelect 콜백

import { useRef, useEffect } from 'react'
// TODO: import cytoscape from 'cytoscape'
// TODO: import dagre from 'cytoscape-dagre'
// TODO: cytoscape.use(dagre)

interface GraphCanvasProps {
  // TODO: elements: cytoscape.ElementDefinition[]
  elements?: unknown[]
  onNodeSelect?: (nodeId: string) => void
}

export default function GraphCanvas({ elements = [], onNodeSelect }: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  // TODO: const cyRef = useRef<cytoscape.Core | null>(null)

  useEffect(() => {
    // TODO: initialize cytoscape instance
    // cyRef.current = cytoscape({ container: containerRef.current, elements, style: [...] })
    // cyRef.current.on('tap', 'node', (evt) => onNodeSelect?.(evt.target.id()))
    // return () => cyRef.current?.destroy()
  }, [])

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-bg-base"
      style={{ minHeight: 400 }}
    />
  )
}
