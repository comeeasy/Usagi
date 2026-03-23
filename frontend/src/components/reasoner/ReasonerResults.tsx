// TODO: 추론 결과 표시
// 탭: Violations / Inferred Axioms
// Violation: severity badge, subject/predicate/object IRIs, 메시지
// Inferred Axiom: subject/predicate/object IRIs, inference_rule, confidence

interface ReasonerResultsProps {
  // TODO: result: ReasonerResult | null
  result?: {
    status: string
    violations?: unknown[]
    inferred_axioms?: unknown[]
    violation_count?: number
    inferred_count?: number
  } | null
  isLoading?: boolean
}

export default function ReasonerResults({ result, isLoading = false }: ReasonerResultsProps) {
  if (isLoading) return <div className="text-text-secondary">Running reasoner...</div>
  if (!result) return null

  return (
    <div>
      {/* TODO: violations tab + inferred axioms tab */}
    </div>
  )
}
