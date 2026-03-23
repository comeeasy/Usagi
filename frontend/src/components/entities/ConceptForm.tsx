// TODO: Concept 생성/수정 폼
// 필드: IRI, label, comment, parent IRIs (multi-select), PropertyRestriction 목록
// 저장/취소 버튼, 유효성 검사

interface ConceptFormProps {
  initialValues?: {
    iri?: string
    label?: string
    comment?: string
    parentIris?: string[]
  }
  onSubmit?: (values: unknown) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

export default function ConceptForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: ConceptFormProps) {
  return (
    <form onSubmit={(e) => { e.preventDefault(); /* TODO */ }}>
      {/* TODO: form fields */}
    </form>
  )
}
