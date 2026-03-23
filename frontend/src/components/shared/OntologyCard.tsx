// TODO: 온톨로지 카드 컴포넌트 (홈 페이지 목록용)
// 이름, 설명, 통계(class/individual/property 수), 마지막 수정일 표시
// 클릭 시 해당 온톨로지로 이동

interface OntologyCardProps {
  // TODO: ontology: Ontology
  ontology?: {
    id: string
    name: string
    description?: string
    stats?: { class_count: number; individual_count: number; property_count: number }
    updated_at?: string
  }
  onClick?: (id: string) => void
}

export default function OntologyCard({ ontology, onClick }: OntologyCardProps) {
  if (!ontology) return null

  return (
    <div
      className="p-4 bg-bg-surface border border-border rounded cursor-pointer hover:border-primary"
      onClick={() => onClick?.(ontology.id)}
    >
      {/* TODO: ontology card content */}
    </div>
  )
}
