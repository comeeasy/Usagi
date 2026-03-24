import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import OntologyCard from '@/components/shared/OntologyCard'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import Pagination from '@/components/shared/Pagination'
import { useOntologies, useCreateOntology } from '@/hooks/useOntology'
import type { OntologyCreate } from '@/types/ontology'

export default function HomePage() {
  const [page, setPage] = useState(1)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { data, isLoading, error } = useOntologies(page, 12)
  const createMutation = useCreateOntology()

  const [form, setForm] = useState<OntologyCreate>({ name: '', base_iri: '', description: '', version: '' })

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await createMutation.mutateAsync({ ...form, version: form.version || undefined, description: form.description || undefined })
    setShowCreateModal(false)
    setForm({ name: '', base_iri: '', description: '', version: '' })
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            Ontology Platform
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Manage your ontologies
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium hover:opacity-80 transition-opacity"
          style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
        >
          <Plus size={16} />
          New Ontology
        </button>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && (
        <div
          className="p-4 rounded-lg border text-sm"
          style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
        >
          Failed to load ontologies: {error.message}
        </div>
      )}

      {data && (
        <>
          {data.items.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-20 rounded-xl border border-dashed gap-4"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
            >
              <p className="text-lg">No ontologies yet</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium hover:opacity-80"
                style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              >
                <Plus size={14} />
                Create your first ontology
              </button>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                {data.items.map((o) => (
                  <OntologyCard
                    key={o.id}
                    ontology={o}
                  />
                ))}
              </div>
              <Pagination
                page={page}
                pageSize={12}
                total={data.total}
                onPageChange={setPage}
              />
            </>
          )}
        </>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50" style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}>
          <div
            className="w-full max-w-md rounded-xl border p-6"
            style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                New Ontology
              </h2>
              <button onClick={() => setShowCreateModal(false)} style={{ color: 'var(--color-text-muted)' }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  Name *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                  placeholder="My Ontology"
                  className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none"
                  style={inputStyle}
                />
              </div>
              <div>
                <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  Base IRI *
                </label>
                <input
                  type="text"
                  value={form.base_iri}
                  onChange={(e) => setForm({ ...form, base_iri: e.target.value })}
                  required
                  placeholder="https://example.org/myontology/"
                  className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono"
                  style={inputStyle}
                />
              </div>
              <div>
                <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={2}
                  placeholder="Optional description"
                  className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none resize-none"
                  style={inputStyle}
                />
              </div>
              <div>
                <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                  Version
                </label>
                <input
                  type="text"
                  value={form.version}
                  onChange={(e) => setForm({ ...form, version: e.target.value })}
                  placeholder="1.0.0"
                  className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none"
                  style={inputStyle}
                />
              </div>

              {createMutation.error && (
                <p className="text-sm" style={{ color: 'var(--color-error)' }}>
                  {createMutation.error.message}
                </p>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
                  style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Ontology'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded text-sm hover:opacity-80"
                  style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
