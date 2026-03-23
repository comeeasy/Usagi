// TODO: 선택 Property 상세 패널
// IRI, 레이블, domain, range, characteristics 표시
// 편집 모드 → PropertyForm 표시

interface RelationDetailPanelProps {
  iri?: string | null
  onClose?: () => void
}

export default function RelationDetailPanel({ iri, onClose }: RelationDetailPanelProps) {
  if (!iri) return null

  return (
    <aside className="w-80 bg-bg-surface border-l border-border overflow-y-auto">
      {/* TODO: relation details for iri={iri} */}
    </aside>
  )
}
