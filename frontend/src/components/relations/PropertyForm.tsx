// TODO: ObjectProperty / DataProperty 생성/수정 폼
// 필드: IRI, label, comment, domain IRI, range IRI/datatype, characteristics 체크박스
// 타입 탭으로 ObjectProperty/DataProperty 전환

interface PropertyFormProps {
  propertyType?: 'object' | 'data'
  initialValues?: {
    iri?: string
    label?: string
    comment?: string
    domainIri?: string
    rangeIri?: string
    characteristics?: string[]
  }
  onSubmit?: (values: unknown) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

export default function PropertyForm({
  propertyType = 'object',
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: PropertyFormProps) {
  return (
    <form onSubmit={(e) => { e.preventDefault(); /* TODO */ }}>
      {/* TODO: form fields for propertyType={propertyType} */}
    </form>
  )
}
