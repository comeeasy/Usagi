import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listConcepts } from '@/api/entities'
import ConceptTreeNode from './ConceptTreeNode'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import Pagination from '@/components/shared/Pagination'

interface Props {
  ontologyId: string
  dataset?: string
  selectedIri: string | null
  onSelect: (iri: string) => void
  onSelectIndividual?: (iri: string) => void
}

const PAGE_SIZE = 50

export default function ConceptTreeView({ ontologyId, dataset, selectedIri, onSelect, onSelectIndividual }: Props) {
  const [page, setPage] = useState(1)

  // 루트 클래스만 로드 (IRI 부모를 선언하지 않는 클래스 = 최상위)
  const rootQuery = useQuery({
    queryKey: ['concepts-root', ontologyId, dataset, page],
    queryFn: () => listConcepts(ontologyId, { root: true, page, pageSize: PAGE_SIZE, dataset }),
    enabled: !!ontologyId,
    staleTime: 60_000,
  })

  if (rootQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12 h-full">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (rootQuery.error) {
    return (
      <div className="p-4 text-sm h-full" style={{ color: 'var(--color-error)' }}>
        Failed to load class hierarchy
      </div>
    )
  }

  const roots = rootQuery.data?.items ?? []
  const total = rootQuery.data?.total ?? 0

  if (total === 0) {
    return (
      <div className="p-4 text-sm h-full" style={{ color: 'var(--color-text-secondary)' }}>
        No concepts found
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 스크롤 가능한 트리 영역 */}
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
            onSelectIndividual={onSelectIndividual}
          />
        ))}
      </div>

      {/* 페이지네이션 */}
      {total > PAGE_SIZE && (
        <div
          className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-t"
          style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
        >
          <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Root classes
          </span>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={(p) => { setPage(p) }}
          />
        </div>
      )}
    </div>
  )
}
