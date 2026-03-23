// TODO: IRI를 간결하게 표시하는 뱃지
// prefix 축약: https://schema.org/ → schema:, https://www.w3.org/2002/07/owl# → owl:
// 클릭 시 전체 IRI 툴팁 표시 또는 클립보드 복사

interface IRIBadgeProps {
  iri: string
  onClick?: (iri: string) => void
}

export default function IRIBadge({ iri, onClick }: IRIBadgeProps) {
  // TODO: implement prefix shortening
  const short = iri // TODO: shorten(iri)

  return (
    <span
      className="font-mono text-xs px-1 py-0.5 bg-bg-elevated border border-border rounded cursor-pointer text-info"
      title={iri}
      onClick={() => onClick?.(iri)}
    >
      {short}
    </span>
  )
}
