// TODO: 선택 Entity 상세 + 편집 폼 슬라이드
// IRI, 레이블, 타입, DataProperty/ObjectProperty 값 목록
// 편집 모드 토글 → ConceptForm / IndividualForm 표시
// ProvenancePanel 임베드

interface EntityDetailPanelProps {
  iri?: string | null
  onClose?: () => void
}

export default function EntityDetailPanel({ iri, onClose }: EntityDetailPanelProps) {
  if (!iri) return null

  return (
    <aside className="w-96 bg-bg-surface border-l border-border overflow-y-auto">
      {/* TODO: entity details + edit form for iri={iri} */}
    </aside>
  )
}
