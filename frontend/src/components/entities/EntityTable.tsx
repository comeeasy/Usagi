// TODO: Concept/Individual 목록 테이블 + 페이지네이션
// 컬럼: IRI, 레이블, 타입, 속성 수
// 행 클릭 → onEntitySelect 콜백
// Pagination 컴포넌트 사용

interface EntityTableProps {
  // TODO: items: (Concept | Individual)[]
  items?: unknown[]
  total?: number
  page?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  onEntitySelect?: (iri: string) => void
}

export default function EntityTable({
  items = [],
  total = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  onEntitySelect,
}: EntityTableProps) {
  return (
    <div>
      {/* TODO: table + pagination */}
    </div>
  )
}
