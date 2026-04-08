/**
 * SchemaPage — Schema 탭 (Concepts + Properties + Individuals 통합)
 *
 * 레이아웃 (모든 경계 드래그 크기 조절 가능):
 *   TOP (4열):
 *     Col1: SchemaLeftPanel — Concept/Property 목록
 *     Col2: SchemaDetailPanel — 선택 항목 Detail
 *     Col3: IndividualsPanel — Concept 선택 시 Individual 목록
 *     Col4: IndividualDetailPanel — Individual 선택 시 세부 정보
 *
 *   BOTTOM (2열):
 *     Left: ConceptGraphPanel — Concept-only 그래프
 *     Right: SchemaReasonerPanel — Reasoner
 */
import { useState, useEffect } from 'react'
import { useParams, useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Panel, PanelGroup } from 'react-resizable-panels'
import OntologyTabs from '@/components/layout/OntologyTabs'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import ResizeHandle from '@/components/shared/ResizeHandle'
import SchemaLeftPanel from '@/components/schema/SchemaLeftPanel'
import SchemaDetailPanel from '@/components/schema/SchemaDetailPanel'
import IndividualsPanel from '@/components/schema/IndividualsPanel'
import IndividualDetailPanel from '@/components/schema/IndividualDetailPanel'
import ConceptGraphPanel from '@/components/schema/ConceptGraphPanel'
import SchemaReasonerPanel from '@/components/schema/SchemaReasonerPanel'
import ConceptForm from '@/components/entities/ConceptForm'
import PropertyForm from '@/components/relations/PropertyForm'
import {
  createConcept,
  updateConcept,
  deleteConcept,
  getConcept,
} from '@/api/entities'
import {
  createObjectProperty,
  createDataProperty,
  updateObjectProperty,
  updateDataProperty,
  deleteProperty,
} from '@/api/relations'
import { getOntology } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import type { Concept, ConceptUpdate } from '@/types/concept'
import type { ObjectProperty, DataProperty, ObjectPropertyCreate, DataPropertyCreate } from '@/types/property'

type SelectionKind = 'concept' | 'property' | null
type PropertyFilter = 'all' | 'object' | 'data'
type ConceptViewMode = 'flat' | 'tree'

type EditingItem =
  | { kind: 'concept'; data: Concept }
  | { kind: 'object-property'; data: ObjectProperty }
  | { kind: 'data-property'; data: DataProperty }

export default function SchemaPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const { dataset } = useDataset()
  const location = useLocation()
  const queryClient = useQueryClient()

  // ── Selection ────────────────────────────────────────────────
  const [selectedIri, setSelectedIri] = useState<string | null>(null)
  const [selectedKind, setSelectedKind] = useState<SelectionKind>(null)
  const [selectedProperty, setSelectedProperty] = useState<ObjectProperty | DataProperty | null>(null)
  const [selectedIndividualIri, setSelectedIndividualIri] = useState<string | null>(null)

  // ── Left panel controls ──────────────────────────────────────
  const [conceptViewMode, setConceptViewMode] = useState<ConceptViewMode>('flat')
  const [propertyFilter, setPropertyFilter] = useState<PropertyFilter>('all')

  // ── Forms ────────────────────────────────────────────────────
  const [showConceptForm, setShowConceptForm] = useState(false)
  const [showPropertyForm, setShowPropertyForm] = useState(false)
  const [editingItem, setEditingItem] = useState<EditingItem | null>(null)

  // ── Feedback ─────────────────────────────────────────────────
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const showFeedbackOk = () => {
    setSaveError(null)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 2000)
  }
  const showFeedbackErr = (err: unknown) => {
    setSaveError(err instanceof Error ? err.message : 'Save failed')
    setTimeout(() => setSaveError(null), 4000)
  }

  // ── Ontology metadata ────────────────────────────────────────
  const ontologyQuery = useQuery({
    queryKey: ['ontology', ontologyId, dataset],
    queryFn: () => getOntology(ontologyId!, dataset),
    enabled: !!ontologyId,
  })
  const iriPrefix = ontologyQuery.data?.base_iri ? `${ontologyQuery.data.base_iri}#` : ''

  // ── Graph 탭에서 Edit 버튼으로 진입 시 처리 ──────────────────
  useEffect(() => {
    const { editIri, entityType } = (location.state ?? {}) as { editIri?: string; entityType?: string }
    if (!editIri || !ontologyId) return
    if (entityType === 'concept' || !entityType) {
      getConcept(ontologyId, editIri, dataset)
        .then((c) => setEditingItem({ kind: 'concept', data: c as Concept }))
        .catch(() => {})
    }
    window.history.replaceState({}, '')
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Mutations ────────────────────────────────────────────────
  const createConceptMutation = useMutation({
    mutationFn: (d: Parameters<typeof createConcept>[1]) => createConcept(ontologyId!, d, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['concepts', ontologyId] })
      setShowConceptForm(false)
      showFeedbackOk()
    },
    onError: showFeedbackErr,
  })

  const updateConceptMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: ConceptUpdate }) =>
      updateConcept(ontologyId!, iri, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['concepts', ontologyId] })
      queryClient.invalidateQueries({ queryKey: ['entity', ontologyId] })
      setEditingItem(null)
      showFeedbackOk()
    },
    onError: showFeedbackErr,
  })

  const deleteConceptMutation = useMutation({
    mutationFn: (iri: string) => deleteConcept(ontologyId!, iri, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['concepts', ontologyId] })
      clearSelection()
    },
    onError: showFeedbackErr,
  })

  const createObjectMutation = useMutation({
    mutationFn: (d: ObjectPropertyCreate) => createObjectProperty(ontologyId!, d, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['object-properties', ontologyId] })
      setShowPropertyForm(false)
      showFeedbackOk()
    },
    onError: showFeedbackErr,
  })

  const createDataMutation = useMutation({
    mutationFn: (d: DataPropertyCreate) => createDataProperty(ontologyId!, d, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-properties', ontologyId] })
      setShowPropertyForm(false)
      showFeedbackOk()
    },
    onError: showFeedbackErr,
  })

  const updateObjectMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: Partial<ObjectPropertyCreate> }) =>
      updateObjectProperty(ontologyId!, iri, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['object-properties', ontologyId] })
      setEditingItem(null)
      showFeedbackOk()
    },
    onError: showFeedbackErr,
  })

  const updateDataMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: Partial<DataPropertyCreate> }) =>
      updateDataProperty(ontologyId!, iri, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-properties', ontologyId] })
      setEditingItem(null)
      showFeedbackOk()
    },
    onError: showFeedbackErr,
  })

  const deletePropertyMutation = useMutation({
    mutationFn: (iri: string) => deleteProperty(ontologyId!, iri, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['object-properties', ontologyId] })
      queryClient.invalidateQueries({ queryKey: ['data-properties', ontologyId] })
      clearSelection()
    },
    onError: showFeedbackErr,
  })

  // ── Handlers ─────────────────────────────────────────────────
  const clearSelection = () => {
    setSelectedIri(null)
    setSelectedKind(null)
    setSelectedProperty(null)
    setSelectedIndividualIri(null)
    setEditingItem(null)
  }

  const handleSelectConcept = (iri: string) => {
    setSelectedIri(iri)
    setSelectedKind('concept')
    setSelectedProperty(null)
    setSelectedIndividualIri(null)
    setShowConceptForm(false)
    setShowPropertyForm(false)
    setEditingItem(null)
  }

  const handleSelectProperty = (iri: string, _kind: 'object' | 'data', property: ObjectProperty | DataProperty) => {
    setSelectedIri(iri)
    setSelectedKind('property')
    setSelectedProperty(property)
    setSelectedIndividualIri(null)
    setShowConceptForm(false)
    setShowPropertyForm(false)
    setEditingItem(null)
  }

  const handleNavigateToConcept = (iri: string) => {
    setSelectedIri(iri)
    setSelectedKind('concept')
    setSelectedProperty(null)
    setSelectedIndividualIri(null)
    setEditingItem(null)
  }

  const handleSelectIndividual = (iri: string) => {
    setSelectedIndividualIri(iri)
  }

  const handleEditConcept = () => {
    if (selectedIri && selectedKind === 'concept') {
      getConcept(ontologyId!, selectedIri, dataset)
        .then((c) => setEditingItem({ kind: 'concept', data: c as Concept }))
        .catch(() => {})
    }
  }

  const handleEditProperty = () => {
    if (!selectedProperty) return
    if ('characteristics' in selectedProperty) {
      setEditingItem({ kind: 'object-property', data: selectedProperty as ObjectProperty })
    } else {
      setEditingItem({ kind: 'data-property', data: selectedProperty as DataProperty })
    }
  }

  const handleDelete = () => {
    if (!selectedIri) return
    if (selectedKind === 'concept') deleteConceptMutation.mutate(selectedIri)
    else if (selectedKind === 'property') deletePropertyMutation.mutate(selectedIri)
  }

  const isShowingForm = showConceptForm || showPropertyForm || !!editingItem

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full overflow-hidden">

        {/* Toast notifications */}
        {saveSuccess && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-sm font-medium shadow-lg"
            style={{ backgroundColor: '#22c55e', color: '#fff' }}>
            Saved successfully
          </div>
        )}
        {saveError && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-lg text-sm font-medium shadow-lg max-w-sm text-center"
            style={{ backgroundColor: 'var(--color-error, #ef4444)', color: '#fff' }}>
            {saveError}
          </div>
        )}

        <OntologyTabs />

        {/* ── 전체: 수직 PanelGroup (TOP ↕ BOTTOM) ────────────── */}
        <PanelGroup direction="vertical" autoSaveId="schema-vertical" className="flex-1 min-h-0">

          {/* ── TOP: 수평 PanelGroup (4열) ───────────────────────── */}
          <Panel defaultSize={50} minSize={20} className="min-h-0">
            <PanelGroup direction="horizontal" autoSaveId="schema-top-horizontal" className="h-full">

              {/* Col 1: Concept + Property list */}
              <Panel defaultSize={20} minSize={10} className="overflow-hidden">
                <SchemaLeftPanel
                  ontologyId={ontologyId!}
                  dataset={dataset}
                  selectedIri={selectedIri}
                  onSelectConcept={handleSelectConcept}
                  onSelectProperty={handleSelectProperty}
                  conceptViewMode={conceptViewMode}
                  onConceptViewModeChange={setConceptViewMode}
                  propertyFilter={propertyFilter}
                  onPropertyFilterChange={setPropertyFilter}
                  onNewConcept={() => { setShowConceptForm(true); setShowPropertyForm(false); setEditingItem(null) }}
                  onNewProperty={() => { setShowPropertyForm(true); setShowConceptForm(false); setEditingItem(null) }}
                />
              </Panel>

              <ResizeHandle direction="horizontal" />

              {/* Col 2: Detail or Form */}
              <Panel defaultSize={25} minSize={10} className="overflow-hidden">
                <div className="flex flex-col h-full overflow-hidden">
                  {/* Concept create */}
                  {showConceptForm && (
                    <div className="flex flex-col h-full overflow-y-auto p-4">
                      <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                        Create Concept
                      </h3>
                      <ConceptForm
                        mode="create"
                        iriPrefix={iriPrefix}
                        onSubmit={(v) => createConceptMutation.mutate({
                          iri: v.iri, label: v.label, comment: v.comment,
                          super_classes: v.superClasses, equivalent_classes: v.equivalentClasses,
                          disjoint_with: v.disjointWith, restrictions: v.restrictions,
                        })}
                        onCancel={() => setShowConceptForm(false)}
                      />
                    </div>
                  )}

                  {/* Property create */}
                  {showPropertyForm && (
                    <div className="flex flex-col h-full overflow-y-auto p-4">
                      <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                        Create Property
                      </h3>
                      <PropertyForm
                        propertyType={propertyFilter === 'data' ? 'data' : 'object'}
                        mode="create"
                        iriPrefix={iriPrefix}
                        onSubmit={(v) => {
                          const vals = v as {
                            iri: string; label: string; comment?: string
                            domain: string[]; range: string[]
                            characteristics: ObjectProperty['characteristics']
                            inverseOf: string; propertyType: string
                          }
                          if (vals.propertyType === 'object') {
                            createObjectMutation.mutate({
                              iri: vals.iri, label: vals.label, comment: vals.comment,
                              domain: vals.domain, range: vals.range,
                              characteristics: vals.characteristics, inverseOf: vals.inverseOf,
                            })
                          } else {
                            createDataMutation.mutate({
                              iri: vals.iri, label: vals.label, comment: vals.comment,
                              domain: vals.domain, range: vals.range as DataProperty['range'],
                            })
                          }
                        }}
                        onCancel={() => setShowPropertyForm(false)}
                      />
                    </div>
                  )}

                  {/* Concept edit */}
                  {editingItem?.kind === 'concept' && (
                    <div className="flex flex-col h-full overflow-y-auto p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Edit Concept</h3>
                        <button onClick={() => setEditingItem(null)} className="p-1 hover:opacity-60" style={{ color: 'var(--color-text-secondary)' }}>×</button>
                      </div>
                      <ConceptForm
                        mode="edit"
                        initialValues={{
                          iri: editingItem.data.iri, label: editingItem.data.label,
                          comment: editingItem.data.comment, superClasses: editingItem.data.super_classes,
                          equivalentClasses: editingItem.data.equivalent_classes,
                          disjointWith: editingItem.data.disjoint_with, restrictions: editingItem.data.restrictions,
                        }}
                        onSubmit={(v) => updateConceptMutation.mutate({
                          iri: editingItem.data.iri,
                          data: {
                            label: v.label, comment: v.comment, super_classes: v.superClasses,
                            equivalent_classes: v.equivalentClasses, disjoint_with: v.disjointWith,
                            restrictions: v.restrictions,
                          },
                        })}
                        onCancel={() => setEditingItem(null)}
                      />
                    </div>
                  )}

                  {/* Object property edit */}
                  {editingItem?.kind === 'object-property' && (
                    <div className="flex flex-col h-full overflow-y-auto p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Edit Object Property</h3>
                        <button onClick={() => setEditingItem(null)} className="p-1 hover:opacity-60" style={{ color: 'var(--color-text-secondary)' }}>×</button>
                      </div>
                      <PropertyForm
                        propertyType="object"
                        mode="edit"
                        initialValues={{
                          iri: editingItem.data.iri, label: editingItem.data.label,
                          comment: editingItem.data.comment, domain: editingItem.data.domain,
                          range: editingItem.data.range as string[],
                          characteristics: editingItem.data.characteristics,
                          inverseOf: editingItem.data.inverseOf,
                        }}
                        onSubmit={(v) => {
                          const vals = v as { label: string; comment?: string; domain: string[]; range: string[]; characteristics: ObjectProperty['characteristics']; inverseOf: string }
                          updateObjectMutation.mutate({
                            iri: editingItem.data.iri,
                            data: { label: vals.label, comment: vals.comment, domain: vals.domain, range: vals.range, characteristics: vals.characteristics, inverseOf: vals.inverseOf },
                          })
                        }}
                        onCancel={() => setEditingItem(null)}
                      />
                    </div>
                  )}

                  {/* Data property edit */}
                  {editingItem?.kind === 'data-property' && (
                    <div className="flex flex-col h-full overflow-y-auto p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Edit Data Property</h3>
                        <button onClick={() => setEditingItem(null)} className="p-1 hover:opacity-60" style={{ color: 'var(--color-text-secondary)' }}>×</button>
                      </div>
                      <PropertyForm
                        propertyType="data"
                        mode="edit"
                        initialValues={{
                          iri: editingItem.data.iri, label: editingItem.data.label,
                          comment: editingItem.data.comment, domain: editingItem.data.domain,
                          range: editingItem.data.range as string[], isFunctional: editingItem.data.isFunctional,
                        }}
                        onSubmit={(v) => {
                          const vals = v as { label: string; comment?: string; domain: string[]; range: DataProperty['range']; isFunctional: boolean }
                          updateDataMutation.mutate({
                            iri: editingItem.data.iri,
                            data: { label: vals.label, comment: vals.comment, domain: vals.domain, range: vals.range, isFunctional: vals.isFunctional },
                          })
                        }}
                        onCancel={() => setEditingItem(null)}
                      />
                    </div>
                  )}

                  {/* Detail panel */}
                  {!isShowingForm && (
                    <SchemaDetailPanel
                      ontologyId={ontologyId!}
                      dataset={dataset}
                      selectedIri={selectedIri}
                      selectedKind={selectedKind}
                      selectedProperty={selectedProperty}
                      onNavigateToConcept={handleNavigateToConcept}
                      onEdit={selectedKind === 'concept' ? handleEditConcept : handleEditProperty}
                      onDelete={handleDelete}
                    />
                  )}
                </div>
              </Panel>

              {/* Col 3: Individuals — Concept 선택 시만 표시 */}
              {selectedKind === 'concept' && selectedIri && !isShowingForm && (
                <>
                  <ResizeHandle direction="horizontal" />
                  <Panel defaultSize={25} minSize={10} className="overflow-hidden">
                    <IndividualsPanel
                      ontologyId={ontologyId!}
                      dataset={dataset}
                      conceptIri={selectedIri}
                      selectedIndividualIri={selectedIndividualIri}
                      onSelectIndividual={handleSelectIndividual}
                    />
                  </Panel>
                </>
              )}

              {/* Col 4: Individual Detail — Individual 선택 시만 표시 */}
              {selectedIndividualIri && !isShowingForm && (
                <>
                  <ResizeHandle direction="horizontal" />
                  <Panel defaultSize={30} minSize={10} className="overflow-hidden">
                    <IndividualDetailPanel
                      ontologyId={ontologyId!}
                      dataset={dataset}
                      individualIri={selectedIndividualIri}
                    />
                  </Panel>
                </>
              )}

            </PanelGroup>
          </Panel>

          <ResizeHandle direction="vertical" />

          {/* ── BOTTOM: 수평 PanelGroup (Graph + Reasoner) ────────── */}
          <Panel defaultSize={50} minSize={15} className="min-h-0">
            <PanelGroup direction="horizontal" autoSaveId="schema-bottom-horizontal" className="h-full">

              {/* Graph */}
              <Panel defaultSize={60} minSize={20} className="overflow-hidden">
                <ConceptGraphPanel
                  ontologyId={ontologyId!}
                  selectedIri={selectedIri}
                />
              </Panel>

              <ResizeHandle direction="horizontal" />

              {/* Reasoner */}
              <Panel defaultSize={40} minSize={15} className="overflow-hidden">
                <SchemaReasonerPanel
                  ontologyId={ontologyId!}
                />
              </Panel>

            </PanelGroup>
          </Panel>

        </PanelGroup>

      </div>
    </ErrorBoundary>
  )
}
