import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

export default function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize)
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  if (total === 0) return null

  return (
    <div className="flex items-center gap-3 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
      <span>
        {start}–{end} / {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          className="p-1 rounded disabled:opacity-40 hover:opacity-80 transition-opacity"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          style={{ color: 'var(--color-text-secondary)' }}
          title="Previous page"
        >
          <ChevronLeft size={16} />
        </button>
        <span className="px-2">
          {page} / {totalPages}
        </span>
        <button
          className="p-1 rounded disabled:opacity-40 hover:opacity-80 transition-opacity"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          style={{ color: 'var(--color-text-secondary)' }}
          title="Next page"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
