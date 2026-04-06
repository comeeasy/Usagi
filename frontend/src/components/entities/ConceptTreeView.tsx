import { useQuery } from '@tanstack/react-query'
import { listConcepts } from '@/api/entities'
import ConceptTreeNode from './ConceptTreeNode'
import LoadingSpinner from '@/components/shared/LoadingSpinner'

interface Props {
  ontologyId: string
  dataset?: string
  selectedIri: string | null
  onSelect: (iri: string) => void
}

export default function ConceptTreeView({ ontologyId, dataset, selectedIri, onSelect }: Props) {
  // 루트 클래스만 로드 (rdfs:subClassOf의 object로 등장하지 않는 것)
  const rootQuery = useQuery({
    queryKey: ['concepts-root', ontologyId, dataset],
    queryFn: () => listConcepts(ontologyId, { root: true, pageSize: 100, dataset }),
    enabled: !!ontologyId,
    staleTime: 60_000,
  })

  if (rootQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (rootQuery.error) {
    return (
      <div className="p-4 text-sm" style={{ color: 'var(--color-error)' }}>
        Failed to load class hierarchy
      </div>
    )
  }

  const roots = rootQuery.data?.items ?? []

  if (roots.length === 0) {
    return (
      <div className="p-4 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
        No concepts found
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto py-1">
      {roots.map((concept) => (
        <ConceptTreeNode
          key={concept.iri}
          concept={concept}
          ontologyId={ontologyId}
          dataset={dataset}
          depth={0}
          selectedIri={selectedIri}
          onSelect={onSelect}
        />
      ))}
      {(rootQuery.data?.total ?? 0) > roots.length && (
        <div className="text-xs px-3 py-1" style={{ color: 'var(--color-text-secondary)' }}>
          +{(rootQuery.data?.total ?? 0) - roots.length} more root classes
        </div>
      )}
    </div>
  )
}
