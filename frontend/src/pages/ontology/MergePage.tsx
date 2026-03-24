import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Merge, CheckCircle } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useOntologies } from '@/hooks/useOntology'
import { useMutation } from '@tanstack/react-query'
import { mergeOntologies } from '@/api/ontologies'

const STRATEGIES = [
  { id: 'union', label: 'Union', desc: 'Merge all triples from both ontologies' },
  { id: 'intersection', label: 'Intersection', desc: 'Keep only shared axioms' },
  { id: 'source_wins', label: 'Source Wins', desc: 'Source ontology takes priority on conflicts' },
  { id: 'target_wins', label: 'Target Wins', desc: 'Current ontology takes priority on conflicts' },
]

export default function MergePage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const [sourceOntologyId, setSourceOntologyId] = useState('')
  const [strategy, setStrategy] = useState('union')

  const { data: ontologiesData } = useOntologies(1, 50)
  const mergeMutation = useMutation({
    mutationFn: () => mergeOntologies(ontologyId!, sourceOntologyId, strategy),
  })

  const otherOntologies = ontologiesData?.items.filter((o) => o.id !== ontologyId) ?? []

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const currentOntology = ontologiesData?.items.find((o) => o.id === ontologyId)
  const sourceOntology = ontologiesData?.items.find((o) => o.id === sourceOntologyId)

  return (
    <div className="flex flex-col h-full">
      <OntologyTabs />

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <h2 className="text-base font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          Merge Ontologies
        </h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
          Merge another ontology into the current one
        </p>

        {/* Merge visualization */}
        <div
          className="flex items-center gap-4 p-4 rounded-lg border mb-6"
          style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
        >
          <div className="flex-1 text-center p-3 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Source</p>
            <p className="font-medium text-sm mt-1" style={{ color: 'var(--color-text-primary)' }}>
              {sourceOntology?.name ?? 'Select source...'}
            </p>
          </div>
          <Merge size={20} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          <div className="flex-1 text-center p-3 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Target (current)</p>
            <p className="font-medium text-sm mt-1" style={{ color: 'var(--color-primary)' }}>
              {currentOntology?.name ?? ontologyId}
            </p>
          </div>
        </div>

        {/* Source selection */}
        <div className="mb-4">
          <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
            Source Ontology *
          </label>
          <select
            value={sourceOntologyId}
            onChange={(e) => setSourceOntologyId(e.target.value)}
            className="w-full px-3 py-2 rounded border text-sm"
            style={inputStyle}
          >
            <option value="">Select an ontology to merge from...</option>
            {otherOntologies.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name} ({o.base_iri})
              </option>
            ))}
          </select>
        </div>

        {/* Strategy */}
        <div className="mb-6">
          <label className="block text-xs mb-2 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
            Merge Strategy
          </label>
          <div className="grid grid-cols-2 gap-2">
            {STRATEGIES.map((s) => (
              <label
                key={s.id}
                className="flex items-start gap-2 p-3 rounded-lg border cursor-pointer"
                style={{
                  borderColor: strategy === s.id ? 'var(--color-primary)' : 'var(--color-border)',
                  backgroundColor: strategy === s.id ? 'rgba(47,129,247,0.1)' : 'var(--color-bg-surface)',
                }}
              >
                <input
                  type="radio"
                  name="strategy"
                  value={s.id}
                  checked={strategy === s.id}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="mt-0.5"
                />
                <div>
                  <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>{s.label}</p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{s.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Result */}
        {mergeMutation.isSuccess && (
          <div
            className="flex items-center gap-2 p-3 rounded-lg border mb-4 text-sm"
            style={{ borderColor: 'var(--color-success)', color: 'var(--color-success)', backgroundColor: 'rgba(63,185,80,0.1)' }}
          >
            <CheckCircle size={16} />
            {mergeMutation.data?.message ?? 'Merge successful'}
            {mergeMutation.data?.merged_triples !== undefined && ` (${mergeMutation.data.merged_triples} triples merged)`}
          </div>
        )}

        {mergeMutation.error && (
          <div
            className="p-3 rounded-lg border mb-4 text-sm"
            style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
          >
            Merge failed: {mergeMutation.error.message}
          </div>
        )}

        <button
          onClick={() => mergeMutation.mutate()}
          disabled={!sourceOntologyId || mergeMutation.isPending}
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
          style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
        >
          {mergeMutation.isPending && <LoadingSpinner size="sm" />}
          <Merge size={14} />
          {mergeMutation.isPending ? 'Merging...' : 'Merge Ontologies'}
        </button>
      </div>
    </div>
  )
}
