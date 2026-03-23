// TODO: SPARQL SELECT 결과 테이블 표시
// 바인딩 변수를 컬럼으로 자동 생성
// IRI 값은 IRIBadge 컴포넌트로 표시
// JSON/Table 뷰 전환 버튼

interface SPARQLResultsTableProps {
  // TODO: results: SparqlResults | null
  results?: {
    variables: string[]
    bindings: Record<string, { type: string; value: string }>[]
  } | null
  isLoading?: boolean
}

export default function SPARQLResultsTable({ results, isLoading = false }: SPARQLResultsTableProps) {
  if (isLoading) return <div className="text-text-secondary">Loading...</div>
  if (!results) return null

  return (
    <div className="overflow-x-auto">
      {/* TODO: dynamic columns from results.variables */}
    </div>
  )
}
