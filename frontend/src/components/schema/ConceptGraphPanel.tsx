/**
 * ConceptGraphPanel — Schema 탭 하단 그래프
 *
 * Concepts API + ObjectProperties API로 직접 그래프 빌드:
 *   - Concept 노드 (owl:Class)
 *   - subClassOf 엣지 (concept.super_classes)
 *   - ObjectProperty 엣지 (domain → range)
 *
 * Individual은 원천적으로 포함되지 않는다.
 * selectedIri: 선택된 노드를 하이라이트하기 위해 사용.
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listConcepts } from '@/api/entities'
import { listObjectProperties } from '@/api/relations'
import { useDataset } from '@/contexts/DatasetContext'
import { useNamedGraphs } from '@/contexts/NamedGraphsContext'
import GraphCanvas, { type CyElement } from '@/components/graph/GraphCanvas'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { Concept } from '@/types/concept'
import type { ObjectProperty } from '@/types/property'

// Backend concepts/properties endpoints validate page_size <= 100.
const PAGE_SIZE = 100

interface Props {
  ontologyId: string
  selectedIri?: string | null
}

function localName(iri: string): string {
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}

export default function ConceptGraphPanel({ ontologyId, selectedIri }: Props) {
  const { dataset } = useDataset()
  const { selectedGraphIris } = useNamedGraphs()

  const conceptsQuery = useQuery({
    queryKey: ['concepts', ontologyId, dataset, 'graph', selectedGraphIris],
    queryFn: () => listConcepts(ontologyId, { pageSize: PAGE_SIZE, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId,
  })

  const propsQuery = useQuery({
    queryKey: ['object-properties', ontologyId, dataset, 'graph', selectedGraphIris],
    queryFn: () => listObjectProperties(ontologyId, { pageSize: PAGE_SIZE, dataset, graphIris: selectedGraphIris }),
    enabled: !!ontologyId,
  })

  const elements = useMemo<CyElement[]>(() => {
    const concepts: Concept[] = conceptsQuery.data?.items ?? []
    const properties: ObjectProperty[] = propsQuery.data?.items ?? []

    const conceptIriSet = new Set(concepts.map((c) => c.iri))

    // 노드: concept 마다 1개
    const nodes: CyElement[] = concepts.map((c) => ({
      data: {
        id: c.iri,
        label: c.label || localName(c.iri),
        kind: 'concept',
        iri: c.iri,
      },
      classes: selectedIri === c.iri ? 'concept selected' : 'concept',
    }))

    const edges: CyElement[] = []

    // subClassOf 엣지
    for (const c of concepts) {
      for (const parent of c.super_classes) {
        if (conceptIriSet.has(parent)) {
          edges.push({
            data: {
              id: `${c.iri}-subClassOf-${parent}`,
              source: c.iri,
              target: parent,
              label: 'subClassOf',
              kind: 'subclass',
            },
            classes: 'subclass',
          })
        }
      }
    }

    // ObjectProperty 엣지: domain → range
    for (const prop of properties) {
      for (const domain of prop.domain) {
        for (const range of prop.range) {
          if (conceptIriSet.has(domain) && conceptIriSet.has(range as string)) {
            const edgeId = `${domain}-${prop.iri}-${range}`
            edges.push({
              data: {
                id: edgeId,
                source: domain,
                target: range as string,
                label: prop.label || localName(prop.iri),
                kind: 'object',
              },
              classes: 'object-property',
            })
          }
        }
      }
    }

    return [...nodes, ...edges]
  }, [conceptsQuery.data, propsQuery.data, selectedIri])

  const isLoading = conceptsQuery.isLoading || propsQuery.isLoading

  return (
    <div className="relative w-full h-full overflow-hidden">
      {/* 로딩 */}
      {isLoading && (
        <div
          className="absolute inset-0 flex items-center justify-center z-10"
          style={{ backgroundColor: 'rgba(0,0,0,0.1)' }}
        >
          <LoadingSpinner size="sm" />
        </div>
      )}

      {/* 빈 상태 */}
      {!isLoading && elements.length === 0 && (
        <div
          className="absolute inset-0 flex items-center justify-center text-sm z-10"
          style={{ color: 'var(--color-text-muted)' }}
        >
          No concepts to display
        </div>
      )}

      <GraphCanvas elements={elements} />
    </div>
  )
}
