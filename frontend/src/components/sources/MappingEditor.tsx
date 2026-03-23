// TODO: PropertyMapping 편집 테이블
// 소스 필드 → Property IRI 매핑 행 목록
// 행 추가/삭제, Property 타입 선택 (data/object), datatype 선택
// R2RML import 버튼 (R2RMLMapper 결과 자동 채우기)

interface MappingEditorProps {
  // TODO: mappings: PropertyMapping[]
  mappings?: unknown[]
  onChange?: (mappings: unknown[]) => void
  onImportR2RML?: (turtle: string) => void
}

export default function MappingEditor({ mappings = [], onChange, onImportR2RML }: MappingEditorProps) {
  return (
    <div>
      {/* TODO: mapping rows table + add/remove buttons */}
    </div>
  )
}
