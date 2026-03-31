import { useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus, X, CheckCircle2, AlertCircle } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import SourceList from '@/components/sources/SourceList'
import SourceConfigForm from '@/components/sources/SourceConfigForm'
import MappingEditor from '@/components/sources/MappingEditor'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listSources, createSource, deleteSource, triggerSync, uploadCsvFile } from '@/api/sources'
import type { BackingSourceCreate, PropertyMapping, UploadResult } from '@/types/source'

export default function SourcesPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [showCreateForm, setShowCreateForm] = useState(false)
  const [mappings, setMappings] = useState<PropertyMapping[]>([])
  const [uploadingSourceId, setUploadingSourceId] = useState<string | null>(null)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

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
      queryClient.invalidateQueries({ queryKey: ['sources', ontologyId] })
    },
  })

  const handleCreate = (config: BackingSourceCreate) => {
    createMutation.mutate({ ...config, property_mappings: mappings })
  }

  const handleDelete = (sourceId: string) => {
    if (confirm('Are you sure you want to delete this source?')) {
      deleteMutation.mutate(sourceId)
    }
  }

  // CSV 업로드 흐름
  const handleUploadClick = (sourceId: string) => {
    setUploadingSourceId(sourceId)
    setUploadResult(null)
    setUploadError(null)
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !uploadingSourceId || !ontologyId) return
    // input 초기화 (같은 파일 재선택 허용)
    e.target.value = ''

    setIsUploading(true)
    setUploadResult(null)
    setUploadError(null)
    try {
      const result = await uploadCsvFile(ontologyId, uploadingSourceId, file)
      setUploadResult(result)
      queryClient.invalidateQueries({ queryKey: ['sources', ontologyId] })
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDismissResult = () => {
    setUploadResult(null)
    setUploadError(null)
    setUploadingSourceId(null)
  }

  // backend returns plain list (not paginated)
  const sourceList = Array.isArray(sourcesQuery.data) ? sourcesQuery.data : []

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <OntologyTabs />

        {/* 업로드 결과 토스트 */}
        {(uploadResult || uploadError || isUploading) && (
          <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-3 rounded-lg shadow-lg border max-w-sm w-full"
            style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)' }}
          >
            {isUploading && (
              <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--color-text-primary)' }}>
                <LoadingSpinner size="sm" />
                Uploading and importing CSV…
              </div>
            )}
            {uploadResult && !isUploading && (
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--color-success)' }}>
                    <CheckCircle2 size={14} />
                    Import complete
                  </div>
                  <button onClick={handleDismissResult} style={{ color: 'var(--color-text-muted)' }}>
                    <X size={14} />
                  </button>
                </div>
                <div className="text-xs mt-1 flex flex-col gap-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                  <span>{uploadResult.rows_read} rows read</span>
                  <span>{uploadResult.triples_inserted} triples → Oxigraph</span>
                  <span>{uploadResult.neo4j_nodes_upserted} nodes → Neo4j</span>
                  {uploadResult.headers.length > 0 && (
                    <span className="font-mono text-xs truncate" style={{ color: 'var(--color-text-muted)' }}>
                      Columns: {uploadResult.headers.join(', ')}
                    </span>
                  )}
                </div>
              </div>
            )}
            {uploadError && !isUploading && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--color-error)' }}>
                  <AlertCircle size={14} />
                  {uploadError}
                </div>
                <button onClick={handleDismissResult} style={{ color: 'var(--color-text-muted)' }}>
                  <X size={14} />
                </button>
              </div>
            )}
          </div>
        )}

        {/* 숨겨진 파일 input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.tsv,.txt"
          className="hidden"
          onChange={handleFileSelected}
        />

        <div className="flex flex-col flex-1 overflow-hidden p-4 gap-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                Backing Sources
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                Configure data sources that populate this ontology with individuals
              </p>
            </div>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium hover:opacity-80"
              style={{
                backgroundColor: showCreateForm ? 'var(--color-bg-elevated)' : 'var(--color-primary)',
                color: showCreateForm ? 'var(--color-text-secondary)' : '#fff',
                border: showCreateForm ? '1px solid var(--color-border)' : 'none',
              }}
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
                <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>
                  Map CSV column names to ontology property IRIs. Upload a CSV first to see available columns.
                </p>
                <MappingEditor mappings={mappings} onChange={setMappings} />
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
              sources={sourceList}
              onEdit={(id) => console.log('edit', id)}
              onDelete={handleDelete}
              onSync={(id) => syncMutation.mutate(id)}
              onUpload={handleUploadClick}
            />
          )}
        </div>
      </div>
    </ErrorBoundary>
  )
}
