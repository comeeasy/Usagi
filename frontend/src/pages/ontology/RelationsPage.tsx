import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import RelationSearchBar from '@/components/relations/RelationSearchBar'
import RelationTable from '@/components/relations/RelationTable'
import RelationDetailPanel from '@/components/relations/RelationDetailPanel'
import PropertyForm from '@/components/relations/PropertyForm'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import EntityGraphPanel from '@/components/graph/EntityGraphPanel'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listObjectProperties,
  listDataProperties,
  createObjectProperty,
  createDataProperty,
  updateObjectProperty,
  updateDataProperty,
} from '@/api/relations'
import { getOntology } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import type { ObjectProperty, DataProperty, ObjectPropertyCreate, DataPropertyCreate } from '@/types/property'

type RelTab = 'object' | 'data'

export default function RelationsPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const { dataset } = useDataset()
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<RelTab>('object')
  const [page, setPage] = useState(1)
  const [selectedIri, setSelectedIri] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [editingProperty, setEditingProperty] = useState<ObjectProperty | DataProperty | null>(null)
  const PAGE_SIZE = 20

  const ontologyQuery = useQuery({
    queryKey: ['ontology', ontologyId, dataset],
    queryFn: () => getOntology(ontologyId!, dataset),
    enabled: !!ontologyId,
  })
  const iriPrefix = ontologyQuery.data?.base_iri ? `${ontologyQuery.data.base_iri}#` : ''

  const objectQuery = useQuery({
    queryKey: ['object-properties', ontologyId, dataset, page, searchQuery],
    queryFn: () =>
      listObjectProperties(ontologyId!, {
        page,
        pageSize: PAGE_SIZE,
        dataset,
        ...(searchQuery ? { search: searchQuery } : {}),
      }),
    enabled: !!ontologyId && tab === 'object',
  })

  const dataQuery = useQuery({
    queryKey: ['data-properties', ontologyId, dataset, page, searchQuery],
    queryFn: () =>
      listDataProperties(ontologyId!, {
        page,
        pageSize: PAGE_SIZE,
        dataset,
        ...(searchQuery ? { search: searchQuery } : {}),
      }),
    enabled: !!ontologyId && tab === 'data',
  })

  const createObjectMutation = useMutation({
    mutationFn: (data: Parameters<typeof createObjectProperty>[1]) => createObjectProperty(ontologyId!, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['object-properties', ontologyId] })
      setShowCreateForm(false)
    },
  })

  const createDataMutation = useMutation({
    mutationFn: (data: Parameters<typeof createDataProperty>[1]) => createDataProperty(ontologyId!, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-properties', ontologyId] })
      setShowCreateForm(false)
    },
  })

  const updateObjectMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: Partial<ObjectPropertyCreate> }) =>
      updateObjectProperty(ontologyId!, iri, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['object-properties', ontologyId] })
      setEditingProperty(null)
    },
  })

  const updateDataMutation = useMutation({
    mutationFn: ({ iri, data }: { iri: string; data: Partial<DataPropertyCreate> }) =>
      updateDataProperty(ontologyId!, iri, data, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-properties', ontologyId] })
      setEditingProperty(null)
    },
  })

  const activeQuery = tab === 'object' ? objectQuery : dataQuery
  const items = (activeQuery.data?.items ?? []).map((item) => {
    const op = item as ObjectProperty
    return {
      iri: item.iri,
      label: item.label,
      kind: tab,
      domain: item.domain,
      range: item.range as string[],
      characteristics: tab === 'object' ? (op.characteristics ?? []) : [],
    }
  })

  const selectedProperty = activeQuery.data?.items.find((i) => i.iri === selectedIri) as
    | ObjectProperty
    | DataProperty
    | undefined

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <OntologyTabs />

        <div className="flex flex-1 overflow-hidden">
          <div className="flex flex-col flex-1 overflow-hidden p-4 gap-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex border rounded overflow-hidden" style={{ borderColor: 'var(--color-border)' }}>
                {(['object', 'data'] as RelTab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTab(t); setPage(1); setSelectedIri(null) }}
                    className="px-4 py-1.5 text-sm capitalize transition-colors"
                    style={{
                      backgroundColor: tab === t ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                      color: tab === t ? '#fff' : 'var(--color-text-secondary)',
                    }}
                  >
                    {t} Properties
                  </button>
                ))}
              </div>
              <button
                onClick={() => setShowCreateForm(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium hover:opacity-80"
                style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              >
                <Plus size={14} />
                New Property
              </button>
            </div>

            <RelationSearchBar onSearch={(q) => { setSearchQuery(q); setPage(1) }} />

            {showCreateForm && (
              <div
                className="p-4 rounded-lg border"
                style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
              >
                <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
                  Create Property
                </h3>
                <PropertyForm
                  propertyType={tab}
                  mode="create"
                  iriPrefix={iriPrefix}
                  onSubmit={(v) => {
                    const vals = v as { iri: string; label: string; comment?: string; domain: string[]; range: string[]; characteristics: string[]; inverseOf: string; propertyType: string }
                    if (vals.propertyType === 'object') {
                      createObjectMutation.mutate({ iri: vals.iri, label: vals.label, comment: vals.comment, domain: vals.domain, range: vals.range, characteristics: vals.characteristics as ObjectProperty['characteristics'], inverseOf: vals.inverseOf })
                    } else {
                      createDataMutation.mutate({ iri: vals.iri, label: vals.label, comment: vals.comment, domain: vals.domain, range: vals.range as DataProperty['range'] })
                    }
                  }}
                  onCancel={() => setShowCreateForm(false)}
                />
              </div>
            )}

            {activeQuery.isLoading && (
              <div className="flex items-center justify-center py-12"><LoadingSpinner size="lg" /></div>
            )}

            {activeQuery.error && (
              <div className="p-4 rounded-lg border text-sm" style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)' }}>
                Error: {activeQuery.error.message}
              </div>
            )}

            {!activeQuery.isLoading && !activeQuery.error && (
              <div className="flex-1 overflow-hidden rounded-lg border" style={{ borderColor: 'var(--color-border)' }}>
                <RelationTable
                  items={items}
                  total={activeQuery.data?.total ?? 0}
                  page={page}
                  pageSize={PAGE_SIZE}
                  onPageChange={setPage}
                  onRelationSelect={setSelectedIri}
                  selectedIri={selectedIri}
                />
              </div>
            )}
          </div>

          {selectedIri && !editingProperty && (
            <aside className="w-96 flex flex-col border-l overflow-hidden"
                   style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}>
              <div className="flex items-center justify-between px-3 py-2 border-b flex-shrink-0"
                   style={{ borderColor: 'var(--color-border)' }}>
                <span className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>Graph</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => selectedProperty ? setEditingProperty(selectedProperty) : undefined}
                    className="px-2 py-1 rounded text-xs hover:opacity-80"
                    style={{ background: 'var(--color-primary)', color: '#fff' }}
                  >
                    Edit
                  </button>
                  <button onClick={() => setSelectedIri(null)}
                    className="p-1 rounded hover:opacity-60" style={{ color: 'var(--color-text-secondary)' }}>
                    ×
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-hidden">
                <EntityGraphPanel ontologyId={ontologyId!} entityIri={selectedIri} />
              </div>
            </aside>
          )}

          {editingProperty && (
            <aside
              className="w-96 flex flex-col border-l overflow-hidden"
              style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
            >
              <div
                className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <h3 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
                  Edit {'characteristics' in editingProperty ? 'Object' : 'Data'} Property
                </h3>
                <button
                  onClick={() => setEditingProperty(null)}
                  className="p-1 rounded hover:opacity-80"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  ×
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <PropertyForm
                  propertyType={'characteristics' in editingProperty ? 'object' : 'data'}
                  mode="edit"
                  initialValues={{
                    iri: editingProperty.iri,
                    label: editingProperty.label,
                    comment: editingProperty.comment,
                    domain: editingProperty.domain,
                    range: editingProperty.range as string[],
                    ...('characteristics' in editingProperty
                      ? { characteristics: editingProperty.characteristics, inverseOf: editingProperty.inverseOf }
                      : { isFunctional: editingProperty.isFunctional }),
                  }}
                  onSubmit={(v) => {
                    const vals = v as { iri: string; label: string; comment?: string; domain: string[]; range: string[]; characteristics: ObjectProperty['characteristics']; inverseOf: string; isFunctional: boolean; propertyType: string }
                    if (vals.propertyType === 'object') {
                      updateObjectMutation.mutate({
                        iri: editingProperty.iri,
                        data: { label: vals.label, comment: vals.comment, domain: vals.domain, range: vals.range, characteristics: vals.characteristics, inverseOf: vals.inverseOf },
                      })
                    } else {
                      updateDataMutation.mutate({
                        iri: editingProperty.iri,
                        data: { label: vals.label, comment: vals.comment, domain: vals.domain, range: vals.range as DataProperty['range'], isFunctional: vals.isFunctional },
                      })
                    }
                  }}
                  onCancel={() => setEditingProperty(null)}
                />
              </div>
            </aside>
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
