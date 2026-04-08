import { useQuery } from '@tanstack/react-query'
import { listIndividuals } from '@/api/entities'
import { useDataset } from '@/contexts/DatasetContext'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { Individual } from '@/types/individual'

interface IndividualsSidebarProps {
  ontologyId: string
  conceptIri: string | null
  /** true이면 사이드바 대신 하단 인라인 스트립으로 렌더링 */
  inline?: boolean
}

export default function IndividualsSidebar({ ontologyId, conceptIri, inline = false }: IndividualsSidebarProps) {
  const { dataset } = useDataset()
  const { selectedGraphIris } = useNamedGraphs()

  const query = useQuery({
    queryKey: ['individuals-by-concept', ontologyId, conceptIri, dataset, selectedGraphIris],
    queryFn: () =>
      listIndividuals(ontologyId, { typeIri: conceptIri!, pageSize: 50, dataset, graphIris: selectedGraphIris }),
    enabled: !!conceptIri,
  })

  if (!conceptIri) return null

  const wrapperStyle = inline
    ? { borderTop: '1px solid var(--color-border)' }
    : { borderLeft: '1px solid var(--color-border)' }
  const wrapperClass = inline
    ? 'flex flex-col overflow-hidden'
    : 'flex flex-col h-full overflow-hidden'
  const listClass = inline ? 'overflow-y-auto max-h-36' : 'flex-1 overflow-y-auto'

  return (
    <div className={wrapperClass} style={wrapperStyle}>
      <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide flex items-center justify-between"
           style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
        <span>Individuals</span>
        {query.data && (
          <span className="font-normal">{query.data.total}</span>
        )}
      </div>

      <div className={listClass}>
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
