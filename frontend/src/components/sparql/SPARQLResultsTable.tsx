import { useState } from 'react'
import IRIBadge from '@/components/shared/IRIBadge'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { SparqlResults, SparqlBinding } from '@/api/sparql'

interface SPARQLResultsTableProps {
  results?: SparqlResults | null
  isLoading?: boolean
}

function BindingCell({ binding }: { binding: SparqlBinding }) {
  if (binding.type === 'uri') {
    return <IRIBadge iri={binding.value} showCopy />
  }
  return (
    <span className="text-sm" style={{ color: 'var(--color-text-primary)' }}>
      {binding.value}
      {binding.datatype && (
        <span className="ml-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          ^^{binding.datatype}
        </span>
      )}
      {binding['xml:lang'] && (
        <span className="ml-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          @{binding['xml:lang']}
        </span>
      )}
    </span>
  )
}

export default function SPARQLResultsTable({ results, isLoading = false }: SPARQLResultsTableProps) {
  const [viewMode, setViewMode] = useState<'table' | 'json'>('table')

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 gap-3">
        <LoadingSpinner size="md" />
        <span style={{ color: 'var(--color-text-secondary)' }}>Executing query...</span>
      </div>
    )
  }

  if (!results) return null

  return (
    <div className="flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          {results.bindings.length} result{results.bindings.length !== 1 ? 's' : ''}
        </span>
        <div
          className="flex border rounded overflow-hidden"
          style={{ borderColor: 'var(--color-border)' }}
        >
          {(['table', 'json'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className="px-3 py-1 text-xs capitalize transition-colors"
              style={{
                backgroundColor: viewMode === mode ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                color: viewMode === mode ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {viewMode === 'table' ? (
        <div className="overflow-x-auto rounded-lg border" style={{ borderColor: 'var(--color-border)' }}>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr style={{ backgroundColor: 'var(--color-bg-surface)' }}>
                {results.variables.map((v) => (
                  <th
                    key={v}
                    className="px-3 py-2 text-left border-b font-medium text-xs"
                    style={{
                      borderColor: 'var(--color-border)',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    ?{v}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.bindings.length === 0 ? (
                <tr>
                  <td
                    colSpan={results.variables.length}
                    className="px-3 py-6 text-center text-sm"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    No results
                  </td>
                </tr>
              ) : (
                results.bindings.map((row, i) => (
                  <tr
                    key={i}
                    className="border-b"
                    style={{ borderColor: 'var(--color-border)' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = 'var(--color-bg-elevated)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent'
                    }}
                  >
                    {results.variables.map((v) => (
                      <td key={v} className="px-3 py-2">
                        {row[v] ? <BindingCell binding={row[v]} /> : <span style={{ color: 'var(--color-text-muted)' }}>—</span>}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <pre
          className="overflow-auto rounded-lg border p-3 text-xs"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
            maxHeight: 400,
          }}
        >
          {JSON.stringify(results, null, 2)}
        </pre>
      )}
    </div>
  )
}
