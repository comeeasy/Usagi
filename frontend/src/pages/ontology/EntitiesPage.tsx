import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import EntitySearchBar from '@/components/entities/EntitySearchBar'
import EntityTable from '@/components/entities/EntityTable'
import EntityDetailPanel from '@/components/entities/EntityDetailPanel'
import ConceptForm from '@/components/entities/ConceptForm'
import IndividualForm from '@/components/entities/IndividualForm'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listConcepts, listIndividuals, createConcept, createIndividual, getConcept, getIndividual } from '@/api/entities'
import type { Concept } from '@/types/concept'
import type { Individual } from '@/types/individual'

type EntityTab = 'concepts' | 'individuals'
type EntityKind = Concept | Individual

export default function EntitiesPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<EntityTab>('concepts')
  const [page, setPage] = useState(1)
  const [selectedIri, setSelectedIri] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [_searchQuery, setSearchQuery] = useState('')
  const PAGE_SIZE = 20

  const conceptsQuery = useQuery({
    queryKey: ['concepts', ontologyId, page],
    queryFn: () => listConcepts(ontologyId!, { page, pageSize: PAGE_SIZE }),
    enabled: !!ontologyId && tab === 'concepts',
  })

  const individualsQuery = useQuery({
    queryKey: ['individuals', ontologyId, page],
    queryFn: () => listIndividuals(ontologyId!, { page, pageSize: PAGE_SIZE }),
    enabled: !!ontologyId && tab === 'individuals',
  })

  const selectedEntityQuery = useQuery<Concept | Individual>({
    queryKey: ['entity', ontologyId, selectedIri, tab],
    queryFn: (): Promise<Concept | Individual> => tab === 'concepts'
      ? getConcept(ontologyId!, selectedIri!)
      : getIndividual(ontologyId!, selectedIri!),
    enabled: !!ontologyId && !!selectedIri,
  })

  const createConceptMutation = useMutation({
    mutationFn: (data: Parameters<typeof createConcept>[1]) => createConcept(ontologyId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['concepts', ontologyId] })
      setShowCreateForm(false)
    },
  })

  const createIndividualMutation = useMutation({
    mutationFn: (data: Parameters<typeof createIndividual>[1]) => createIndividual(ontologyId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['individuals', ontologyId] })
      setShowCreateForm(false)
    },
  })

  const activeQuery = tab === 'concepts' ? conceptsQuery : individualsQuery
  const items = (activeQuery.data?.items ?? []).map((item) => {
    const c = item as Concept
    const ind = item as Individual
    return {
      iri: item.iri,
      label: item.label,
      type: tab === 'concepts' ? 'concept' : 'individual' as const,
      count: tab === 'concepts'
        ? (c.restrictions?.length ?? 0)
        : ((ind.data_properties?.length ?? 0) + (ind.object_properties?.length ?? 0)),
    }
  })

  const handleTabChange = (t: EntityTab) => {
    setTab(t)
    setPage(1)
    setSelectedIri(null)
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <OntologyTabs />

        <div className="flex flex-1 overflow-hidden">
          {/* Main content */}
          <div className="flex flex-col flex-1 overflow-hidden p-4 gap-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex border rounded overflow-hidden" style={{ borderColor: 'var(--color-border)' }}>
                {(['concepts', 'individuals'] as EntityTab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => handleTabChange(t)}
                    className="px-4 py-1.5 text-sm capitalize transition-colors"
                    style={{
                      backgroundColor: tab === t ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                      color: tab === t ? '#fff' : 'var(--color-text-secondary)',
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>

              <button
                onClick={() => setShowCreateForm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium hover:opacity-80"
                style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              >
                <Plus size={14} />
                New {tab === 'concepts' ? 'Concept' : 'Individual'}
              </button>
            </div>

            <EntitySearchBar
              onSearch={(q) => setSearchQuery(q)}
            />

            {/* Create form */}
            {showCreateForm && (
              <div
                className="p-4 rounded-lg border"
                style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
              >
                <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                  Create {tab === 'concepts' ? 'Concept' : 'Individual'}
                </h3>
                {tab === 'concepts' ? (
                  <ConceptForm
                    mode="create"
                    onSubmit={(v) => createConceptMutation.mutate(v as Parameters<typeof createConcept>[1])}
                    onCancel={() => setShowCreateForm(false)}
                  />
                ) : (
                  <IndividualForm
                    mode="create"
                    onSubmit={(v) => {
                      const vals = v as { iri: string; label: string; typeIris: string[]; dataProperties: unknown[]; objectProperties: unknown[] }
                      createIndividualMutation.mutate({
                        iri: vals.iri,
                        label: vals.label,
                        type_iris: vals.typeIris,
                        data_properties: vals.dataProperties as Individual['data_properties'],
                        object_properties: vals.objectProperties as Individual['object_properties'],
                      })
                    }}
                    onCancel={() => setShowCreateForm(false)}
                  />
                )}
              </div>
            )}

            {/* Table */}
            {activeQuery.isLoading && (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="lg" />
              </div>
            )}

            {activeQuery.error && (
              <div
                className="p-4 rounded-lg border text-sm"
                style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)' }}
              >
                Error: {activeQuery.error.message}
              </div>
            )}

            {!activeQuery.isLoading && !activeQuery.error && (
              <div className="flex-1 overflow-hidden rounded-lg border" style={{ borderColor: 'var(--color-border)' }}>
                <EntityTable
                  items={items}
                  total={activeQuery.data?.total ?? 0}
                  page={page}
                  pageSize={PAGE_SIZE}
                  onPageChange={setPage}
                  onEntitySelect={setSelectedIri}
                  selectedIri={selectedIri}
                />
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedIri && (
            <EntityDetailPanel
              entity={selectedEntityQuery.data as EntityKind | null}
              iri={selectedIri}
              onClose={() => setSelectedIri(null)}
            />
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
