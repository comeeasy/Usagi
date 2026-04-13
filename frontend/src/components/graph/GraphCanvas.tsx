/**
 * GraphCanvas — React Flow 기반 그래프 캔버스
 *
 * CyElement[] 인터페이스를 유지하여 기존 컴포넌트 호환성 보장.
 * 내부적으로 dagre 레이아웃으로 노드 위치를 계산한다.
 */
import { useEffect, useMemo, useCallback, memo } from 'react'
import {
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  useReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
  type EdgeProps,
} from '@xyflow/react'
import dagre from '@dagrejs/dagre'
import '@xyflow/react/dist/style.css'

// ── 공개 타입 (기존 CyElement 호환) ────────────────────────────────────────────

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

// ── dagre 레이아웃 ─────────────────────────────────────────────────────────────

const NODE_W = 120
const NODE_H = 36

function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80, edgesep: 20 })

  for (const n of nodes) {
    const isIndividual = n.type === 'individual'
    g.setNode(n.id, { width: isIndividual ? 80 : NODE_W, height: isIndividual ? 80 : NODE_H })
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target)
  }

  dagre.layout(g)

  return nodes.map((n) => {
    const pos = g.node(n.id)
    const isIndividual = n.type === 'individual'
    const w = isIndividual ? 80 : NODE_W
    const h = isIndividual ? 80 : NODE_H
    return { ...n, position: { x: pos.x - w / 2, y: pos.y - h / 2 } }
  })
}

// ── CyElement → React Flow 변환 ────────────────────────────────────────────────

function cyElementsToFlow(elements: CyElement[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []
  const nodeIds = new Set<string>()

  for (const el of elements) {
    if (el.data.source !== undefined) continue // edge
    nodeIds.add(el.data.id)
  }

  for (const el of elements) {
    if (el.data.source !== undefined) {
      // edge
      if (!nodeIds.has(el.data.source) || !nodeIds.has(el.data.target!)) continue
      const classes = el.classes ?? ''
      const isSubclass = classes.includes('subclass')
      const isObject   = classes.includes('object-property')
      edges.push({
        id: el.data.id,
        source: el.data.source,
        target: el.data.target!,
        label: el.data.label ?? '',
        type: isSubclass ? 'subclassEdge' : isObject ? 'objectEdge' : 'defaultEdge',
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        data: { label: el.data.label ?? '' },
      })
    } else {
      // node
      const classes = el.classes ?? ''
      const isConcept    = classes.includes('concept')
      const isIndividual = classes.includes('individual')
      const type = isConcept ? 'concept' : isIndividual ? 'individual' : 'concept'
      nodes.push({
        id: el.data.id,
        type,
        position: { x: 0, y: 0 },
        data: { label: el.data.label ?? el.data.id, iri: el.data.iri ?? el.data.id },
      })
    }
  }

  return { nodes, edges }
}

// ── 커스텀 노드 ────────────────────────────────────────────────────────────────

const ConceptNode = memo(({ data, selected }: NodeProps) => (
  <div
    style={{
      width: NODE_W,
      height: NODE_H,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: 6,
      fontSize: 11,
      fontWeight: 500,
      color: '#fff',
      background: selected ? '#58a6ff' : '#2F81F7',
      border: selected ? '2px solid #fff' : '2px solid transparent',
      boxShadow: selected ? '0 0 0 2px #2F81F7' : '0 1px 4px rgba(0,0,0,0.4)',
      padding: '0 6px',
      overflow: 'hidden',
      wordBreak: 'break-word',
      textAlign: 'center',
      lineHeight: 1.2,
      cursor: 'pointer',
    }}
    title={(data as { iri: string }).iri}
  >
    <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
    <span style={{ maxWidth: NODE_W - 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {data.label as string}
    </span>
    <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
  </div>
))
ConceptNode.displayName = 'ConceptNode'

const IndividualNode = memo(({ data, selected }: NodeProps) => (
  <div
    style={{
      width: 80,
      height: 80,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '50%',
      fontSize: 10,
      fontWeight: 500,
      color: '#fff',
      background: selected ? '#56d364' : '#3FB950',
      border: selected ? '2px solid #fff' : '2px solid transparent',
      boxShadow: selected ? '0 0 0 2px #3FB950' : '0 1px 4px rgba(0,0,0,0.4)',
      padding: 6,
      overflow: 'hidden',
      wordBreak: 'break-word',
      textAlign: 'center',
      lineHeight: 1.2,
      cursor: 'pointer',
    }}
    title={(data as { iri: string }).iri}
  >
    <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
    <span style={{ maxWidth: 68, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
      {data.label as string}
    </span>
    <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
  </div>
))
IndividualNode.displayName = 'IndividualNode'

const nodeTypes = { concept: ConceptNode, individual: IndividualNode }

// ── 커스텀 엣지 ────────────────────────────────────────────────────────────────

function makeEdge(color: string, dashed = false) {
  return memo(({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps) => {
    const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })
    const label = (data as { label?: string })?.label
    return (
      <>
        <BaseEdge
          id={id}
          path={edgePath}
          style={{
            stroke: color,
            strokeWidth: 1.5,
            strokeDasharray: dashed ? '5 3' : undefined,
          }}
        />
        {label && (
          <EdgeLabelRenderer>
            <div
              style={{
                position: 'absolute',
                transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                fontSize: 9,
                color: '#8B949E',
                background: 'var(--color-bg-base, #0d1117)',
                padding: '1px 3px',
                borderRadius: 2,
                pointerEvents: 'none',
                whiteSpace: 'nowrap',
                maxWidth: 80,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
              className="nodrag nopan"
            >
              {label}
            </div>
          </EdgeLabelRenderer>
        )}
      </>
    )
  })
}

const DefaultEdge  = makeEdge('#4a5568')
const SubclassEdge = makeEdge('#4a5568', true)
const ObjectEdge   = makeEdge('#A371F7')

DefaultEdge.displayName  = 'DefaultEdge'
SubclassEdge.displayName = 'SubclassEdge'
ObjectEdge.displayName   = 'ObjectEdge'

const edgeTypes = { defaultEdge: DefaultEdge, subclassEdge: SubclassEdge, objectEdge: ObjectEdge }

// ── 내부 Flow 컴포넌트 (ReactFlowProvider 안에서 useReactFlow 가능) ─────────────

interface FlowInnerProps {
  elements: CyElement[]
  onNodeSelect?: (nodeId: string) => void
  onNodeDoubleClick?: (nodeId: string) => void
}

function FlowInner({ elements, onNodeSelect, onNodeDoubleClick }: FlowInnerProps) {
  const { fitView } = useReactFlow()

  const { nodes: rawNodes, edges: rawEdges } = useMemo(
    () => cyElementsToFlow(elements),
    [elements],
  )

  const laidOutNodes = useMemo(
    () => applyDagreLayout(rawNodes, rawEdges),
    [rawNodes, rawEdges],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(laidOutNodes)
  const [edges, , onEdgesChange]         = useEdgesState(rawEdges)

  // elements 변경 시 노드/엣지 갱신 + fit
  useEffect(() => {
    setNodes(laidOutNodes)
    requestAnimationFrame(() => fitView({ padding: 0.15, duration: 300 }))
  }, [laidOutNodes, setNodes, fitView])

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => onNodeSelect?.(node.id),
    [onNodeSelect],
  )

  const handleNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => onNodeDoubleClick?.(node.id),
    [onNodeDoubleClick],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodeClick={handleNodeClick}
      onNodeDoubleClick={handleNodeDoubleClick}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.2}
      maxZoom={2}
      style={{ background: 'var(--color-bg-base, #0d1117)' }}
      proOptions={{ hideAttribution: true }}
    >
      <Background color="#30363D" gap={20} size={1} />
      <Controls
        style={{
          background: 'var(--color-bg-elevated, #161b22)',
          borderColor: 'var(--color-border, #30363d)',
          color: 'var(--color-text-secondary, #8b949e)',
        }}
        showInteractive={false}
      />
      <MiniMap
        nodeColor={(n) => n.type === 'individual' ? '#3FB950' : '#2F81F7'}
        maskColor="rgba(0,0,0,0.6)"
        style={{
          background: 'var(--color-bg-elevated, #161b22)',
          border: '1px solid var(--color-border, #30363d)',
        }}
      />
    </ReactFlow>
  )
}

// ── 공개 컴포넌트 ──────────────────────────────────────────────────────────────

interface GraphCanvasProps {
  elements?: CyElement[]
  layout?: string
  onNodeSelect?: (nodeId: string) => void
  onNodeDoubleClick?: (nodeId: string) => void
  cyRef?: React.MutableRefObject<unknown>
}

export default function GraphCanvas({
  elements = [],
  onNodeSelect,
  onNodeDoubleClick,
}: GraphCanvasProps) {
  return (
    <div className="w-full h-full" style={{ minHeight: 400 }}>
      <ReactFlowProvider>
        <FlowInner
          elements={elements}
          onNodeSelect={onNodeSelect}
          onNodeDoubleClick={onNodeDoubleClick}
        />
      </ReactFlowProvider>
    </div>
  )
}
