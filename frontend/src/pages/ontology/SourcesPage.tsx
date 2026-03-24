import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus, X } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import SourceList from '@/components/sources/SourceList'
import SourceConfigForm from '@/components/sources/SourceConfigForm'
import MappingEditor from '@/components/sources/MappingEditor'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listSources, createSource, deleteSource, triggerSync } from '@/api/sources'
import type { BackingSourceCreate, PropertyMapping } from '@/types/source'

export default function SourcesPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const queryClient = useQueryClient()

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [mappings, setMappings] = useState<PropertyMapping[]>([])
  const [_syncingId, setSyncingId] = useState<string | null>(null)

  const sourcesQuery = useQuery({
    queryKey: ['sources', ontologyId],
    queryFn: () => listSources(ontologyId!),
    enabled: !!ontologyId,
  })

  const createMutation = useMutation({
    mutationFn: (data: BackingSourceCreate) => createSource(ontologyId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', ontologyId] })
      setShowCreateForm(false)
      setMappings([])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => deleteSource(ontologyId!, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', ontologyId] })
    },
  })

  const syncMutation = useMutation({
    mutationFn: (sourceId: string) => triggerSync(ontologyId!, sourceId),
    onSuccess: () => {
      setSyncingId(null)
      queryClient.invalidateQueries({ queryKey: ['sources', ontologyId] })
    },
    onError: () => setSyncingId(null),
  })

  const handleCreate = (config: BackingSourceCreate) => {
    createMutation.mutate({
      ...config,
      property_mappings: mappings,
    })
  }

  const handleSync = (sourceId: string) => {
    setSyncingId(sourceId)
    syncMutation.mutate(sourceId)
  }

  const handleDelete = (sourceId: string) => {
    if (confirm('Are you sure you want to delete this source?')) {
      deleteMutation.mutate(sourceId)
    }
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <OntologyTabs />

        <div className="flex flex-col flex-1 overflow-hidden p-4 gap-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                Backing Sources
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                Configure data sources that populate this ontology
              </p>
            </div>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium hover:opacity-80"
              style={{ backgroundColor: showCreateForm ? 'var(--color-bg-elevated)' : 'var(--color-primary)', color: showCreateForm ? 'var(--color-text-secondary)' : '#fff', border: showCreateForm ? '1px solid var(--color-border)' : 'none' }}
            >
              {showCreateForm ? <X size={14} /> : <Plus size={14} />}
              {showCreateForm ? 'Cancel' : 'Add Source'}
            </button>
          </div>

          {/* Create form */}
          {showCreateForm && (
            <div
              className="rounded-lg border p-4 flex flex-col gap-4"
              style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
            >
              <h3 className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>New Source</h3>
              <SourceConfigForm
                mode="create"
                onSubmit={handleCreate}
                onCancel={() => { setShowCreateForm(false); setMappings([]) }}
              />
              <div>
                <h4 className="font-medium text-sm mb-2" style={{ color: 'var(--color-text-primary)' }}>Property Mappings</h4>
                <MappingEditor
                  mappings={mappings}
                  onChange={setMappings}
                />
              </div>
            </div>
          )}

          {/* Loading */}
          {sourcesQuery.isLoading && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          )}

          {/* Error */}
          {sourcesQuery.error && (
            <div className="p-4 rounded-lg border text-sm" style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)' }}>
              Error: {sourcesQuery.error.message}
            </div>
          )}

          {/* Sources list */}
          {!sourcesQuery.isLoading && !sourcesQuery.error && (
            <SourceList
              sources={sourcesQuery.data?.items ?? []}
              onEdit={(id) => console.log('edit', id)}
              onDelete={handleDelete}
              onSync={handleSync}
            />
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
