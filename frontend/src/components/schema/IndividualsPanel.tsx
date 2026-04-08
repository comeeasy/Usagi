/**
 * IndividualsPanel — Schema 탭 3열: 선택된 Concept의 Individual 목록
 */
import { useQuery } from '@tanstack/react-query'
import { listIndividuals } from '@/api/entities'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { Individual } from '@/types/individual'

interface Props {
  ontologyId: string
  dataset: string
  conceptIri: string
  selectedIndividualIri: string | null
  onSelectIndividual: (iri: string) => void
}

export default function IndividualsPanel({
  ontologyId,
  dataset,
  conceptIri,
  selectedIndividualIri,
  onSelectIndividual,
}: Props) {
  const query = useQuery({
    queryKey: ['individuals-by-concept', ontologyId, conceptIri, dataset],
    queryFn: () => listIndividuals(ontologyId, { typeIri: conceptIri, pageSize: 100, dataset }),
    enabled: !!conceptIri,
  })

  return (
    <div
      data-testid="schema-individuals-panel"
      className="flex flex-col h-full overflow-hidden border-l"
      style={{ borderColor: 'var(--color-border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b flex-shrink-0"
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          borderColor: 'var(--color-border)',
        }}
      >
        <span className="text-xs font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
          Individuals
        </span>
        {query.data && (
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            {query.data.total}
          </span>
        )}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {query.isLoading && (
          <div className="flex justify-center py-6">
            <LoadingSpinner size="sm" />
          </div>
        )}
        {query.isSuccess && query.data.items.length === 0 && (
          <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
            No individuals
          </div>
        )}
        {query.isSuccess && query.data.items.map((ind: Individual) => {
          const label = ind.label || ind.iri.split(/[#/]/).at(-1) || ind.iri
          const isSelected = selectedIndividualIri === ind.iri
          return (
            <div
              key={ind.iri}
              onClick={() => onSelectIndividual(ind.iri)}
              className="px-3 py-2 text-sm cursor-pointer border-b transition-colors"
              style={{
                borderColor: 'var(--color-border)',
                backgroundColor: isSelected ? 'var(--color-bg-elevated)' : 'transparent',
                color: isSelected ? 'var(--color-primary)' : 'var(--color-text-primary)',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--color-bg-surface)'
              }}
              onMouseLeave={(e) => {
                if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent'
              }}
              title={ind.iri}
            >
              {label}
            </div>
          )
        })}
      </div>
    </div>
  )
}
