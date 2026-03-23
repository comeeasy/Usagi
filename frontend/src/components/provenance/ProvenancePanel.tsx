// TODO: 개체(Individual)의 Provenance 이력 표시
// 소스 ID, 소스 타입, 생성 시간, Named Graph IRI 목록
// 각 provenance 항목에서 원본 소스로 이동 링크

interface ProvenancePanelProps {
  // TODO: records: ProvenanceRecord[]
  records?: unknown[]
}

export default function ProvenancePanel({ records = [] }: ProvenancePanelProps) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text-secondary mb-2">Provenance</h3>
      {/* TODO: provenance records list */}
    </section>
  )
}
