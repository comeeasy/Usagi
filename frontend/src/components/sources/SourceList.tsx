// TODO: Backing Source 목록 표시
// 소스 이름, 타입(JDBC/API/Stream), 활성화 상태, 마지막 동기화 시간
// 수정/삭제/동기화 버튼

interface SourceListProps {
  // TODO: sources: BackingSource[]
  sources?: unknown[]
  onEdit?: (sourceId: string) => void
  onDelete?: (sourceId: string) => void
  onSync?: (sourceId: string) => void
}

export default function SourceList({ sources = [], onEdit, onDelete, onSync }: SourceListProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* TODO: source items */}
    </div>
  )
}
