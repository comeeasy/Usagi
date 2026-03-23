// TODO: 페이지네이션 컴포넌트
// 이전/다음 버튼, 페이지 번호 표시, 전체 건수 표시
// 첫/마지막 페이지 비활성화 처리

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

export default function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="flex items-center gap-2 text-sm text-text-secondary">
      {/* TODO: prev/next buttons + page info */}
      <span>{(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} / {total}</span>
    </div>
  )
}
