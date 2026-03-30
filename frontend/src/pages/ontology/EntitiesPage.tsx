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
import { listConcepts, listIndividuals, createConcept, createIndividual, getConcept, getIndividual, updateConcept, updateIndividual, deleteConcept, deleteIndividual } from '@/api/entities'
import type { Concept, ConceptUpdate } from '@/types/concept'
import type { Individual, IndividualUpdate } from '@/types/individual'

type EntityTab = 'concepts' | 'individuals'
type EntityKind = Concept | Individual

export default function EntitiesPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<EntityTab>('concepts')
  const [page, setPage] = useState(1)
  const [selectedIri, setSelectedIri] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [editingEntity, setEditingEntity] = useState<EntityKind | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const PAGE_SIZE = 20

  const conceptsQuery = useQuery({
    queryKey: ['concepts', ontologyId, page, searchQuery],
    queryFn: () => listConcepts(ontologyId!, { page, pageSize: PAGE_SIZE, ...(searchQuery ? { search: searchQuery } : {}) }),
    enabled: !!ontologyId && tab === 'concepts',
  })

  const individualsQuery = useQuery({
    queryKey: ['individuals', ontologyId, page, searchQuery],
    queryFn: () => listIndividuals(ontologyId!, { page, pageSize: PAGE_SIZE, ...(searchQuery ? { search: searchQuery } : {}) }),
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

  const showSaveSuccess = () => {
    setSaveError(null)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 2000)
  }

  const showSaveError = (err: unknown) => {
    const msg = err instanceof Error ? err.message : 'Save failed'
    setSaveError(msg)
    setTimeout(() => setSaveError(null), 4000)
  }

  const updateConceptMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: ConceptUpdate }) => updateConcept(ontologyId!, iri, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['entity', ontologyId, updated.iri, 'concepts'], updated)
      queryClient.invalidateQueries({ queryKey: ['concepts', ontologyId] })
      setEditingEntity(null)
      showSaveSuccess()
    },
    onError: showSaveError,
  })

  const deleteConceptMutation = useMutation({
    mutationFn: (iri: string) => deleteConcept(ontologyId!, iri),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['concepts', ontologyId] })
      setSelectedIri(null)
    },
    onError: showSaveError,
  })

  const deleteIndividualMutation = useMutation({
    mutationFn: (iri: string) => deleteIndividual(ontologyId!, iri),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['individuals', ontologyId] })
      setSelectedIri(null)
    },
    onError: showSaveError,
  })

  const updateIndividualMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: IndividualUpdate }) => updateIndividual(ontologyId!, iri, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['entity', ontologyId, (updated as Individual).iri, 'individuals'], updated)
      queryClient.invalidateQueries({ queryKey: ['individuals', ontologyId] })
      setEditingEntity(null)
      showSaveSuccess()
    },
    onError: showSaveError,
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

  const handleEntitySelect = (iri: string) => {
    if (editingEntity) setEditingEntity(null)
    setSelectedIri(iri)
  }

  const handleTabChange = (t: EntityTab) => {
    setTab(t)
    setPage(1)
    setSelectedIri(null)
    setEditingEntity(null)
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        {saveSuccess && (
          <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-sm font-medium shadow-lg"
            style={{ backgroundColor: '#22c55e', color: '#fff' }}
          >
            Saved successfully
          </div>
        )}
        {saveError && (
          <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-sm font-medium shadow-lg max-w-sm text-center"
            style={{ backgroundColor: 'var(--color-error, #ef4444)', color: '#fff' }}
          >
            {saveError}
          </div>
        )}
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
                className="rounded-lg border overflow-y-auto flex-shrink-0"
                style={{ maxHeight: '65vh', backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
              >
              <div className="p-4">
                <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                  Create {tab === 'concepts' ? 'Concept' : 'Individual'}
                </h3>
                {tab === 'concepts' ? (
                  <ConceptForm
                    mode="create"
                    onSubmit={(v) => createConceptMutation.mutate({
                      iri: v.iri,
                      label: v.label,
                      comment: v.comment,
                      super_classes: v.superClasses,
                      equivalent_classes: v.equivalentClasses,
                      disjoint_with: v.disjointWith,
                      restrictions: v.restrictions,
                    })}
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
                        types: vals.typeIris,
                        data_property_values: vals.dataProperties as Individual['data_property_values'],
                        object_property_values: vals.objectProperties as Individual['object_property_values'],
                      })
                    }}
                    onCancel={() => setShowCreateForm(false)}
                  />
                )}
              </div>
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
                  onEntitySelect={handleEntitySelect}
                  selectedIri={selectedIri}
                />
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedIri && !editingEntity && (
            <EntityDetailPanel
              entity={selectedEntityQuery.data as EntityKind | null}
              iri={selectedIri}
              onClose={() => setSelectedIri(null)}
              onEdit={() => selectedEntityQuery.data ? setEditingEntity(selectedEntityQuery.data as EntityKind) : undefined}
              onDelete={() => tab === 'concepts'
                ? deleteConceptMutation.mutate(selectedIri)
                : deleteIndividualMutation.mutate(selectedIri)
              }
            />
          )}

          {/* Edit form panel */}
          {editingEntity && (
            <aside
              className="w-96 flex flex-col border-l overflow-hidden"
              style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
            >
              <div
                className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
                  Edit {tab === 'concepts' ? 'Concept' : 'Individual'}
                </h3>
                <button
                  onClick={() => setEditingEntity(null)}
                  className="p-1 rounded hover:opacity-80"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  ×
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                {tab === 'concepts' ? (
                  <ConceptForm
                    mode="edit"
                    initialValues={{
                      iri: editingEntity.iri,
                      label: editingEntity.label,
                      comment: (editingEntity as Concept).comment,
                      superClasses: (editingEntity as Concept).super_classes,
                      equivalentClasses: (editingEntity as Concept).equivalent_classes,
                      disjointWith: (editingEntity as Concept).disjoint_with,
                      restrictions: (editingEntity as Concept).restrictions,
                    }}
                    onSubmit={(v) => updateConceptMutation.mutate({
                      iri: editingEntity.iri,
                      data: {
                        label: v.label,
                        comment: v.comment,
                        super_classes: v.superClasses,
                        equivalent_classes: v.equivalentClasses,
                        disjoint_with: v.disjointWith,
                        restrictions: v.restrictions,
                      },
                    })}
                    onCancel={() => setEditingEntity(null)}
                  />
                ) : (
                  <IndividualForm
                    mode="edit"
                    initialValues={{
                      iri: editingEntity.iri,
                      label: editingEntity.label,
                      typeIris: (editingEntity as Individual).types,
                      dataProperties: (editingEntity as Individual).data_property_values,
                      objectProperties: (editingEntity as Individual).object_property_values,
                    }}
                    onSubmit={(v) => {
                      const vals = v as { iri: string; label: string; typeIris: string[]; dataProperties: Individual['data_property_values']; objectProperties: Individual['object_property_values'] }
                      updateIndividualMutation.mutate({
                        iri: editingEntity.iri,
                        data: {
                          label: vals.label,
                          types: vals.typeIris,
                          data_property_values: vals.dataProperties,
                          object_property_values: vals.objectProperties,
                        },
                      })
                    }}
                    onCancel={() => setEditingEntity(null)}
                  />
                )}
              </div>
            </aside>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
