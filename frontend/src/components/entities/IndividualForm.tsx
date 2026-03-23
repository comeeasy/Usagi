// TODO: Individual 생성/수정 폼
// 필드: IRI, label, type IRIs (multi-select), DataProperty 값 목록, ObjectProperty 값 목록
// 동적 필드 추가/삭제, 저장/취소 버튼

interface IndividualFormProps {
  initialValues?: {
    iri?: string
    label?: string
    typeIris?: string[]
    dataProperties?: unknown[]
    objectProperties?: unknown[]
  }
  onSubmit?: (values: unknown) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

export default function IndividualForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: IndividualFormProps) {
  return (
    <form onSubmit={(e) => { e.preventDefault(); /* TODO */ }}>
      {/* TODO: form fields */}
    </form>
  )
}
