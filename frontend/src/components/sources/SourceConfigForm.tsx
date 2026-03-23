// TODO: Backing Source 설정 폼
// SourceType 선택 탭: JDBC / API / Stream / File
// 각 타입별 설정 필드 동적 표시
// concept IRI 선택, IRI template 입력

interface SourceConfigFormProps {
  initialValues?: unknown
  onSubmit?: (values: unknown) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

export default function SourceConfigForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: SourceConfigFormProps) {
  return (
    <form onSubmit={(e) => { e.preventDefault(); /* TODO */ }}>
      {/* TODO: source type tabs + config fields */}
    </form>
  )
}
