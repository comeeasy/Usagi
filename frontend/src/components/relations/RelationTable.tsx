// TODO: ObjectProperty/DataProperty 목록 테이블 + 페이지네이션
// 컬럼: IRI, 레이블, domain, range, characteristics
// 행 클릭 → onRelationSelect 콜백

interface RelationTableProps {
  items?: unknown[]
  total?: number
  page?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  onRelationSelect?: (iri: string) => void
}

export default function RelationTable({
  items = [],
  total = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  onRelationSelect,
}: RelationTableProps) {
  return (
    <div>
      {/* TODO: table + pagination */}
    </div>
  )
}
