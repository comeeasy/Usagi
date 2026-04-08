/**
 * SchemaReasonerPanel — Schema 탭 하단 우측 Reasoner 패널
 */
import { useState } from 'react'
import { Brain, Play, ChevronDown, ChevronUp } from 'lucide-react'
import ReasonerResults from '@/components/reasoner/ReasonerResults'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useReasoner } from '@/hooks/useReasoner'

interface Props {
  ontologyId: string
  entityIris?: string[]
}

export default function SchemaReasonerPanel({ ontologyId, entityIris = [] }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [checkConsistency, setCheckConsistency] = useState(true)
  const [includeInferences, setIncludeInferences] = useState(true)
  const [profile, setProfile] = useState<'EL' | 'RL' | 'QL' | 'FULL'>('EL')

  const { runMutation, resultQuery, jobId } = useReasoner(ontologyId)

  const isRunning =
    runMutation.isPending ||
    resultQuery.data?.status === 'pending' ||
    resultQuery.data?.status === 'running'

  const handleRun = () => {
    runMutation.mutate({
      subgraph_entity_iris: entityIris.length ? entityIris : undefined,
      include_inferences: includeInferences,
      check_consistency: checkConsistency,
      reasoner_profile: profile,
    })
  }

  return (
    <div
      className="flex flex-col h-full overflow-hidden border-l"
      style={{
        borderColor: 'var(--color-border)',
        backgroundColor: 'var(--color-bg-surface)',
      }}
    >
      {/* Header bar */}
      <div
        className="flex items-center gap-2 px-3 py-2 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <Brain size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
        <span className="text-xs font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
          Reasoner
        </span>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="p-0.5 rounded hover:opacity-60"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {/* Status chip */}
        {resultQuery.data?.result && !isRunning && (
          <div className="flex items-center gap-1.5 ml-1">
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                background: resultQuery.data.result.consistent
                  ? 'rgba(34,197,94,0.15)'
                  : 'rgba(239,68,68,0.15)',
                color: resultQuery.data.result.consistent
                  ? '#22c55e'
                  : 'var(--color-error)',
              }}
            >
              {resultQuery.data.result.consistent ? 'Consistent' : 'Inconsistent'}
            </span>
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {resultQuery.data.result.violations.length} violations ·{' '}
              {resultQuery.data.result.inferred_axioms.length} inferred
            </span>
          </div>
        )}
        {isRunning && (
          <div className="flex items-center gap-1 ml-1">
            <LoadingSpinner size="sm" />
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Running…</span>
          </div>
        )}
      </div>

      {/* Config (expanded) */}
      {expanded && (
        <div
          className="flex items-center gap-4 px-3 py-2 flex-wrap border-b flex-shrink-0"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <label className="flex items-center gap-1.5 text-xs cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
            <input
              type="checkbox"
              checked={checkConsistency}
              onChange={(e) => setCheckConsistency(e.target.checked)}
              className="w-3 h-3"
            />
            Check consistency
          </label>
          <label className="flex items-center gap-1.5 text-xs cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
            <input
              type="checkbox"
              checked={includeInferences}
              onChange={(e) => setIncludeInferences(e.target.checked)}
              className="w-3 h-3"
            />
            Include inferences
          </label>
          <div className="flex items-center gap-1.5">
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Profile:</span>
            <select
              value={profile}
              onChange={(e) => setProfile(e.target.value as typeof profile)}
              className="text-xs px-1.5 py-0.5 rounded border"
              style={{
                backgroundColor: 'var(--color-bg-elevated)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
            >
              {(['EL', 'RL', 'QL', 'FULL'] as const).map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium hover:opacity-80 disabled:opacity-50 ml-auto"
            style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
          >
            {isRunning ? <LoadingSpinner size="sm" /> : <Play size={10} />}
            {isRunning ? 'Running…' : 'Run Reasoner'}
          </button>
          {runMutation.error && (
            <span className="text-xs w-full" style={{ color: 'var(--color-error)' }}>
              {runMutation.error.message}
            </span>
          )}
        </div>
      )}

      {/* Quick Run button when collapsed */}
      {!expanded && (
        <div className="flex items-center justify-center flex-1 px-3">
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium hover:opacity-80 disabled:opacity-50"
            style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
          >
            {isRunning ? <LoadingSpinner size="sm" /> : <Play size={11} />}
            {isRunning ? 'Running…' : 'Run Reasoner'}
          </button>
        </div>
      )}

      {/* Results (expanded) */}
      {expanded && (
        <div className="flex-1 overflow-y-auto p-3">
          {!jobId && !runMutation.isPending && (
            <p className="text-xs text-center py-4" style={{ color: 'var(--color-text-muted)' }}>
              Configure options and click Run Reasoner
            </p>
          )}
          <ReasonerResults
            result={resultQuery.data ?? null}
            isLoading={isRunning}
          />
        </div>
      )}
    </div>
  )
}
