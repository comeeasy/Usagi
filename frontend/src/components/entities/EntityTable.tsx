import IRIBadge from '@/components/shared/IRIBadge'
import Pagination from '@/components/shared/Pagination'

interface EntityRow {
  iri: string
  label?: string
  type?: string
  count?: number
}

interface EntityTableProps {
  items?: EntityRow[]
  total?: number
  page?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  onEntitySelect?: (iri: string) => void
  selectedIri?: string | null
}

export default function EntityTable({
  items = [],
  total = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  onEntitySelect,
  selectedIri,
}: EntityTableProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr
              className="border-b text-left"
              style={{ borderColor: 'var(--color-border)' }}
            >
              {['IRI', 'Label', 'Type', 'Properties'].map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 font-medium text-xs"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-3 py-8 text-center text-sm"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  No entities found
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.iri}
                  className="border-b cursor-pointer transition-colors"
                  style={{
                    borderColor: 'var(--color-border)',
                    backgroundColor:
                      selectedIri === item.iri
                        ? 'var(--color-bg-elevated)'
                        : 'transparent',
                  }}
                  onClick={() => onEntitySelect?.(item.iri)}
                  onMouseEnter={(e) => {
                    if (selectedIri !== item.iri)
                      e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)'
                  }}
                  onMouseLeave={(e) => {
                    if (selectedIri !== item.iri)
                      e.currentTarget.style.backgroundColor = 'transparent'
                  }}
                >
                  <td className="px-3 py-2 max-w-xs">
                    <IRIBadge iri={item.iri} showCopy />
                  </td>
                  <td className="px-3 py-2" style={{ color: 'var(--color-text-primary)' }}>
                    {item.label ?? '—'}
                  </td>
                  <td className="px-3 py-2">
                    {item.type && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor:
                            item.type === 'concept'
                              ? 'rgba(47,129,247,0.15)'
                              : 'rgba(63,185,80,0.15)',
                          color:
                            item.type === 'concept'
                              ? 'var(--color-primary)'
                              : 'var(--color-success)',
                          border: '1px solid',
                          borderColor:
                            item.type === 'concept'
                              ? 'var(--color-primary)'
                              : 'var(--color-success)',
                        }}
                      >
                        {item.type}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2" style={{ color: 'var(--color-text-secondary)' }}>
                    {item.count ?? '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div
          className="px-3 py-2 border-t flex items-center justify-between"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={onPageChange ?? (() => {})}
          />
        </div>
      )}
    </div>
  )
}
