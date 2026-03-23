// TODO: 선택된 노드 상세, 우측 슬라이드 패널
// 노드 타입 (Concept / Individual) 분기 표시
// IRI, 레이블, 속성 목록, Provenance 정보 표시
// 편집 버튼 → ConceptForm / IndividualForm 열기

interface NodeDetailPanelProps {
  nodeId?: string | null
  onClose?: () => void
}

export default function NodeDetailPanel({ nodeId, onClose }: NodeDetailPanelProps) {
  if (!nodeId) return null

  return (
    <aside className="w-80 bg-bg-surface border-l border-border overflow-y-auto">
      {/* TODO: node details for nodeId={nodeId} */}
    </aside>
  )
}
