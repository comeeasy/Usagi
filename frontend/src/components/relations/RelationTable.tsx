import IRIBadge from '@/components/shared/IRIBadge'
import Pagination from '@/components/shared/Pagination'

interface RelationRow {
  iri: string
  label?: string
  domain?: string[]
  range?: string[]
  characteristics?: string[]
  kind?: 'object' | 'data'
}

interface RelationTableProps {
  items?: RelationRow[]
  total?: number
  page?: number
  pageSize?: number
  onPageChange?: (page: number) => void
  onRelationSelect?: (iri: string) => void
  selectedIri?: string | null
}

export default function RelationTable({
  items = [],
  total = 0,
  page = 1,
  pageSize = 20,
  onPageChange,
  onRelationSelect,
  selectedIri,
}: RelationTableProps) {
  return (
    <div className="flex flex-col h-full">
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-left" style={{ borderColor: 'var(--color-border)' }}>
              {['IRI', 'Label', 'Type', 'Domain', 'Range', 'Characteristics'].map((col) => (
                <th key={col} className="px-3 py-2 font-medium text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
                  No relations found
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr
                  key={item.iri}
                  className="border-b cursor-pointer transition-colors"
                  style={{
                    borderColor: 'var(--color-border)',
                    backgroundColor: selectedIri === item.iri ? 'var(--color-bg-elevated)' : 'transparent',
                  }}
                  onClick={() => onRelationSelect?.(item.iri)}
                  onMouseEnter={(e) => {
                    if (selectedIri !== item.iri) e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)'
                  }}
                  onMouseLeave={(e) => {
                    if (selectedIri !== item.iri) e.currentTarget.style.backgroundColor = 'transparent'
                  }}
                >
                  <td className="px-3 py-2 max-w-xs"><IRIBadge iri={item.iri} showCopy /></td>
                  <td className="px-3 py-2" style={{ color: 'var(--color-text-primary)' }}>{item.label ?? '—'}</td>
                  <td className="px-3 py-2">
                    {item.kind && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: item.kind === 'object' ? 'rgba(163,113,247,0.15)' : 'rgba(210,153,34,0.15)',
                          color: item.kind === 'object' ? '#A371F7' : 'var(--color-warning)',
                          border: '1px solid',
                          borderColor: item.kind === 'object' ? '#A371F7' : 'var(--color-warning)',
                        }}
                      >
                        {item.kind}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(item.domain ?? []).slice(0, 2).map((d) => <IRIBadge key={d} iri={d} />)}
                      {(item.domain ?? []).length > 2 && (
                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                          +{(item.domain ?? []).length - 2}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(item.range ?? []).slice(0, 2).map((r) => <IRIBadge key={r} iri={r} />)}
                      {(item.range ?? []).length > 2 && (
                        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                          +{(item.range ?? []).length - 2}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {(item.characteristics ?? []).map((c) => (
                        <span key={c} className="text-xs px-1 py-0.5 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)', color: 'var(--color-text-muted)' }}>
                          {c}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div className="px-3 py-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <Pagination page={page} pageSize={pageSize} total={total} onPageChange={onPageChange ?? (() => {})} />
        </div>
      )}
    </div>
  )
}
