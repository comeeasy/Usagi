import { useQuery } from '@tanstack/react-query'
import { listIndividuals } from '@/api/entities'
import { useDataset } from '@/contexts/DatasetContext'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { Individual } from '@/types/individual'

interface IndividualsSidebarProps {
  ontologyId: string
  conceptIri: string | null
}

export default function IndividualsSidebar({ ontologyId, conceptIri }: IndividualsSidebarProps) {
  const { dataset } = useDataset()

  const query = useQuery({
    queryKey: ['individuals-by-concept', ontologyId, conceptIri, dataset],
    queryFn: () =>
      listIndividuals(ontologyId, { typeIri: conceptIri!, pageSize: 50, dataset }),
    enabled: !!conceptIri,
  })

  if (!conceptIri) return null

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ borderLeft: '1px solid var(--color-border)' }}>
      <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide flex items-center justify-between"
           style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
        <span>Individuals</span>
        {query.data && (
          <span className="font-normal">{query.data.total}</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {query.isPending && (
          <div className="flex justify-center py-4">
            <LoadingSpinner size="sm" />
          </div>
        )}

        {query.isSuccess && query.data.items.length === 0 && (
          <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
            No individuals
          </div>
        )}

        {query.isSuccess && query.data.items.map((ind: Individual) => (
          <div
            key={ind.iri}
            className="px-3 py-2 text-sm cursor-default hover:opacity-80"
            style={{ borderBottom: '1px solid var(--color-border)' }}
            title={ind.iri}
          >
            {ind.label || ind.iri.split(/[#/]/).at(-1)}
          </div>
        ))}
      </div>
    </div>
  )
}
