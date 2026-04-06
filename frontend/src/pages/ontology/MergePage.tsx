import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Merge, CheckCircle, AlertTriangle, ChevronRight, RotateCcw } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useOntologies } from '@/hooks/useOntology'
import { useMutation } from '@tanstack/react-query'
import {
  previewMerge,
  mergeOntologies,
  type ConflictItem,
  type ConflictResolution,
} from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'

type Choice = ConflictResolution['choice']

const CHOICE_LABELS: Record<Choice, string> = {
  'keep-target': 'Keep Current',
  'keep-source': 'Use Source',
  'merge-both': 'Keep Both',
}

const CONFLICT_TYPE_LABELS: Record<ConflictItem['conflict_type'], string> = {
  label: 'Label',
  domain: 'Domain',
  range: 'Range',
  superClass: 'Super Class',
}

export default function MergePage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const { dataset } = useDataset()
  const [sourceOntologyId, setSourceOntologyId] = useState('')
  const [step, setStep] = useState<'select' | 'preview' | 'done'>('select')
  const [conflicts, setConflicts] = useState<ConflictItem[]>([])
  const [autoMergeableCount, setAutoMergeableCount] = useState(0)
  const [resolutions, setResolutions] = useState<Record<string, Choice>>({})

  const { data: ontologiesData } = useOntologies(1, 50)
  const otherOntologies = ontologiesData?.items.filter((o) => o.id !== ontologyId) ?? []
  const currentOntology = ontologiesData?.items.find((o) => o.id === ontologyId)
  const sourceOntology = ontologiesData?.items.find((o) => o.id === sourceOntologyId)

  const previewMutation = useMutation({
    mutationFn: () => previewMerge(ontologyId!, sourceOntologyId, dataset),
    onSuccess: (data) => {
      setConflicts(data.conflicts)
      setAutoMergeableCount(data.auto_mergeable_count)
      // 기본값: keep-target
      const defaults: Record<string, Choice> = {}
      data.conflicts.forEach((c) => {
        defaults[`${c.iri}::${c.conflict_type}`] = 'keep-target'
      })
      setResolutions(defaults)
      setStep('preview')
    },
  })

  const mergeMutation = useMutation({
    mutationFn: () => {
      const resolutionList: ConflictResolution[] = conflicts.map((c) => ({
        iri: c.iri,
        conflict_type: c.conflict_type,
        choice: resolutions[`${c.iri}::${c.conflict_type}`] ?? 'keep-target',
      }))
      return mergeOntologies(ontologyId!, sourceOntologyId, resolutionList, dataset)
    },
    onSuccess: () => setStep('done'),
  })

  function setChoice(iri: string, conflictType: string, choice: Choice) {
    setResolutions((prev) => ({ ...prev, [`${iri}::${conflictType}`]: choice }))
  }

  function reset() {
    setStep('select')
    setSourceOntologyId('')
    setConflicts([])
    setResolutions({})
    previewMutation.reset()
    mergeMutation.reset()
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  return (
    <div className="flex flex-col h-full">
      <OntologyTabs />

      <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
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

        {/* ── STEP: select ── */}
        {step === 'select' && (
          <>
            <div className="mb-6">
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

            {previewMutation.isError && (
              <div
                className="p-3 rounded-lg border mb-4 text-sm"
                style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
              >
                Preview failed: {previewMutation.error.message}
              </div>
            )}

            <button
              onClick={() => previewMutation.mutate()}
              disabled={!sourceOntologyId || previewMutation.isPending}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              {previewMutation.isPending ? <LoadingSpinner size="sm" /> : <ChevronRight size={14} />}
              {previewMutation.isPending ? 'Analyzing conflicts...' : 'Preview & Resolve Conflicts'}
            </button>
          </>
        )}

        {/* ── STEP: preview ── */}
        {step === 'preview' && (
          <>
            {/* Summary */}
            <div className="flex gap-3 mb-5">
              <div
                className="flex-1 p-3 rounded-lg border text-center"
                style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
              >
                <p className="text-xl font-bold" style={{ color: conflicts.length > 0 ? 'var(--color-warning, #d29922)' : 'var(--color-success)' }}>
                  {conflicts.length}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>Conflicts</p>
              </div>
              <div
                className="flex-1 p-3 rounded-lg border text-center"
                style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
              >
                <p className="text-xl font-bold" style={{ color: 'var(--color-success)' }}>
                  {autoMergeableCount}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>Auto-merge</p>
              </div>
            </div>

            {/* Conflict list */}
            {conflicts.length === 0 ? (
              <div
                className="flex items-center gap-2 p-4 rounded-lg border mb-5 text-sm"
                style={{ borderColor: 'var(--color-success)', color: 'var(--color-success)', backgroundColor: 'rgba(63,185,80,0.1)' }}
              >
                <CheckCircle size={16} />
                No conflicts detected. All {autoMergeableCount} entities will be merged automatically.
              </div>
            ) : (
              <div className="mb-5">
                <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                  Resolve conflicts — choose which value to keep for each:
                </p>
                <div className="flex flex-col gap-2">
                  {conflicts.map((c) => {
                    const key = `${c.iri}::${c.conflict_type}`
                    const current = resolutions[key] ?? 'keep-target'
                    const shortIri = c.iri.includes('#') ? c.iri.split('#').pop() : c.iri.split('/').pop()
                    return (
                      <div
                        key={key}
                        className="p-3 rounded-lg border"
                        style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle size={12} style={{ color: 'var(--color-warning, #d29922)', flexShrink: 0 }} />
                          <span className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>
                            {shortIri}
                          </span>
                          <span
                            className="text-xs px-1.5 py-0.5 rounded"
                            style={{ backgroundColor: 'var(--color-bg-elevated)', color: 'var(--color-text-muted)' }}
                          >
                            {CONFLICT_TYPE_LABELS[c.conflict_type]}
                          </span>
                        </div>

                        {/* Values */}
                        <div className="grid grid-cols-2 gap-2 mb-2 text-xs">
                          <div className="p-2 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)' }}>
                            <p style={{ color: 'var(--color-text-muted)' }}>Current</p>
                            <p className="mt-0.5 font-mono break-all" style={{ color: 'var(--color-text-primary)' }}>
                              {c.target_value || '—'}
                            </p>
                          </div>
                          <div className="p-2 rounded" style={{ backgroundColor: 'var(--color-bg-elevated)' }}>
                            <p style={{ color: 'var(--color-text-muted)' }}>Source</p>
                            <p className="mt-0.5 font-mono break-all" style={{ color: 'var(--color-text-primary)' }}>
                              {c.source_value || '—'}
                            </p>
                          </div>
                        </div>

                        {/* Choice buttons */}
                        <div className="flex gap-1.5">
                          {(['keep-target', 'keep-source', 'merge-both'] as Choice[]).map((choice) => (
                            <button
                              key={choice}
                              onClick={() => setChoice(c.iri, c.conflict_type, choice)}
                              className="flex-1 py-1 text-xs rounded border font-medium"
                              style={{
                                borderColor: current === choice ? 'var(--color-primary)' : 'var(--color-border)',
                                backgroundColor: current === choice ? 'rgba(47,129,247,0.15)' : 'var(--color-bg-elevated)',
                                color: current === choice ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                              }}
                            >
                              {CHOICE_LABELS[choice]}
                            </button>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {mergeMutation.isError && (
              <div
                className="p-3 rounded-lg border mb-4 text-sm"
                style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
              >
                Merge failed: {mergeMutation.error.message}
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={reset}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded text-sm border hover:opacity-80"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)', backgroundColor: 'var(--color-bg-elevated)' }}
              >
                <RotateCcw size={13} />
                Back
              </button>
              <button
                onClick={() => mergeMutation.mutate()}
                disabled={mergeMutation.isPending}
                className="flex flex-1 items-center justify-center gap-2 py-2.5 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
                style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
              >
                {mergeMutation.isPending ? <LoadingSpinner size="sm" /> : <Merge size={14} />}
                {mergeMutation.isPending ? 'Merging...' : `Merge (${conflicts.length} resolved + ${autoMergeableCount} auto)`}
              </button>
            </div>
          </>
        )}

        {/* ── STEP: done ── */}
        {step === 'done' && (
          <div className="text-center py-8">
            <CheckCircle size={40} className="mx-auto mb-3" style={{ color: 'var(--color-success)' }} />
            <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
              Merge complete
            </p>
            <p className="text-xs mb-6" style={{ color: 'var(--color-text-muted)' }}>
              {mergeMutation.data?.triple_count ?? 0} triples in target ontology
            </p>
            <button
              onClick={reset}
              className="flex items-center gap-1.5 mx-auto px-4 py-2 rounded text-sm border hover:opacity-80"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)', backgroundColor: 'var(--color-bg-elevated)' }}
            >
              <RotateCcw size={13} />
              Merge another
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
