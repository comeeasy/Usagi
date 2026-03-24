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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listObjectProperties,
  listDataProperties,
  createObjectProperty,
  createDataProperty,
} from '@/api/relations'
import type { ObjectProperty, DataProperty } from '@/types/property'

type RelTab = 'object' | 'data'

export default function RelationsPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const queryClient = useQueryClient()

  const [tab, setTab] = useState<RelTab>('object')
  const [page, setPage] = useState(1)
  const [selectedIri, setSelectedIri] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const PAGE_SIZE = 20

  const objectQuery = useQuery({
    queryKey: ['object-properties', ontologyId, page],
    queryFn: () => listObjectProperties(ontologyId!, { page, pageSize: PAGE_SIZE }),
    enabled: !!ontologyId && tab === 'object',
  })

  const dataQuery = useQuery({
    queryKey: ['data-properties', ontologyId, page],
    queryFn: () => listDataProperties(ontologyId!, { page, pageSize: PAGE_SIZE }),
    enabled: !!ontologyId && tab === 'data',
  })

  const createObjectMutation = useMutation({
    mutationFn: (data: Parameters<typeof createObjectProperty>[1]) => createObjectProperty(ontologyId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['object-properties', ontologyId] })
      setShowCreateForm(false)
    },
  })

  const createDataMutation = useMutation({
    mutationFn: (data: Parameters<typeof createDataProperty>[1]) => createDataProperty(ontologyId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-properties', ontologyId] })
      setShowCreateForm(false)
    },
  })

  const activeQuery = tab === 'object' ? objectQuery : dataQuery
  const items = (activeQuery.data?.items ?? []).map((item) => {
    const op = item as ObjectProperty
    const dp = item as DataProperty
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

            <RelationSearchBar onSearch={() => {}} />

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

          {selectedIri && (
            <RelationDetailPanel
              property={selectedProperty ?? null}
              iri={selectedIri}
              onClose={() => setSelectedIri(null)}
            />
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
