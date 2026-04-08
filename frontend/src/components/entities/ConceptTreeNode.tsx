import { useState } from 'react'
import { ChevronRight, ChevronDown, Loader2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listSubclasses, listIndividuals } from '@/api/entities'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import type { Concept } from '@/types/concept'

interface Props {
  concept: Concept
  ontologyId: string
  dataset?: string
  depth?: number
  selectedIri: string | null
  onSelect: (iri: string) => void
  onSelectIndividual?: (iri: string) => void
}

export default function ConceptTreeNode({
  concept,
  ontologyId,
  dataset,
  depth = 0,
  selectedIri,
  onSelect,
  onSelectIndividual,
}: Props) {
  const [expanded, setExpanded] = useState(false)
  const hasChildren = concept.subclass_count > 0
  const hasIndividuals = concept.individual_count > 0
  const { selectedGraphIris } = useNamedGraphs()

  const childrenQuery = useQuery({
    queryKey: ['subclasses', ontologyId, concept.iri, dataset, selectedGraphIris],
    queryFn: () => listSubclasses(ontologyId, concept.iri, { pageSize: 200, dataset, graphIris: selectedGraphIris }),
    enabled: expanded && hasChildren,
    staleTime: 60_000,
  })

  const individualsQuery = useQuery({
    queryKey: ['concept-type-individuals', ontologyId, concept.iri, dataset, selectedGraphIris],
    queryFn: () => listIndividuals(ontologyId, { pageSize: 100, dataset, typeIri: concept.iri, graphIris: selectedGraphIris }),
    enabled: expanded && hasIndividuals,
    staleTime: 60_000,
  })

  const isSelected = selectedIri === concept.iri
  const indentPx = depth * 20
  const childIndentPx = (depth + 1) * 20

  const isLoading = (hasChildren && childrenQuery.isFetching) || (hasIndividuals && individualsQuery.isFetching && !individualsQuery.data)

  return (
    <div>
      {/* Row */}
      <div
        className="flex items-center gap-1 px-2 py-1 cursor-pointer rounded text-sm select-none"
        style={{
          paddingLeft: `${8 + indentPx}px`,
          backgroundColor: isSelected ? 'var(--color-primary)' : undefined,
          color: isSelected ? '#fff' : 'var(--color-text-primary)',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-bg-elevated)'
        }}
        onMouseLeave={(e) => {
          if (!isSelected) (e.currentTarget as HTMLElement).style.backgroundColor = ''
        }}
      >
        {/* Toggle button */}
        <span
          className="flex-shrink-0 w-4 h-4 flex items-center justify-center"
          onClick={(e) => {
            e.stopPropagation()
            if (hasChildren || hasIndividuals) setExpanded((v) => !v)
          }}
        >
          {hasChildren || hasIndividuals ? (
            isLoading ? (
              <Loader2 size={12} className="animate-spin opacity-60" />
            ) : expanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )
          ) : (
            <span className="w-3 h-3 rounded-full inline-block opacity-30" style={{ backgroundColor: 'currentColor' }} />
          )}
        </span>

        {/* Label */}
        <span
          className="flex-1 truncate"
          onClick={() => onSelect(concept.iri)}
          title={concept.iri}
        >
          {concept.label || concept.iri}
        </span>

        {/* Badges */}
        <span className="flex-shrink-0 flex gap-1 ml-1">
          {hasIndividuals && (
            <span
              className="text-xs px-1.5 rounded-full"
              style={{
                backgroundColor: isSelected ? 'rgba(255,255,255,0.25)' : 'var(--color-bg-elevated)',
                color: isSelected ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              {concept.individual_count}
            </span>
          )}
          {hasChildren && (
            <span
              className="text-xs px-1.5 rounded-full"
              style={{
                backgroundColor: isSelected ? 'rgba(255,255,255,0.20)' : 'var(--color-primary)',
                color: '#fff',
                opacity: isSelected ? 1 : 0.8,
              }}
            >
              {concept.subclass_count}
            </span>
          )}
        </span>
      </div>

      {/* Children */}
      {expanded && (
        <div>
          {/* Subclasses */}
          {hasChildren && childrenQuery.data && (
            <>
              {childrenQuery.data.items.map((child) => (
                <ConceptTreeNode
                  key={child.iri}
                  concept={child}
                  ontologyId={ontologyId}
                  dataset={dataset}
                  depth={depth + 1}
                  selectedIri={selectedIri}
                  onSelect={onSelect}
                  onSelectIndividual={onSelectIndividual}
                />
              ))}
              {childrenQuery.data.total > childrenQuery.data.items.length && (
                <div
                  className="text-xs px-2 py-1"
                  style={{ paddingLeft: `${8 + childIndentPx}px`, color: 'var(--color-text-secondary)' }}
                >
                  +{childrenQuery.data.total - childrenQuery.data.items.length} more subclasses
                </div>
              )}
            </>
          )}

          {/* Individuals */}
          {hasIndividuals && individualsQuery.data && (
            <>
              {individualsQuery.data.items.map((ind) => {
                const isIndSelected = selectedIri === ind.iri
                return (
                  <div
                    key={ind.iri}
                    className="flex items-center gap-1 px-2 py-0.5 cursor-pointer text-sm select-none rounded"
                    style={{
                      paddingLeft: `${8 + childIndentPx}px`,
                      backgroundColor: isIndSelected ? 'var(--color-primary)' : undefined,
                      color: isIndSelected ? '#fff' : 'var(--color-text-secondary)',
                    }}
                    onMouseEnter={(e) => {
                      if (!isIndSelected) (e.currentTarget as HTMLElement).style.backgroundColor = 'var(--color-bg-elevated)'
                    }}
                    onMouseLeave={(e) => {
                      if (!isIndSelected) (e.currentTarget as HTMLElement).style.backgroundColor = ''
                    }}
                    onClick={() => onSelectIndividual?.(ind.iri)}
                    title={ind.iri}
                  >
                    <span className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: isIndSelected ? '#fff' : 'var(--color-primary)', opacity: 0.8 }}
                      />
                    </span>
                    <span className="flex-1 truncate italic">{ind.label || ind.iri}</span>
                  </div>
                )
              })}
              {individualsQuery.data.total > individualsQuery.data.items.length && (
                <div
                  className="text-xs px-2 py-1"
                  style={{ paddingLeft: `${8 + childIndentPx}px`, color: 'var(--color-text-secondary)' }}
                >
                  +{individualsQuery.data.total - individualsQuery.data.items.length} more individuals
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
