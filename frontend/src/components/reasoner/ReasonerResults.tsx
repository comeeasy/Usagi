import { useState } from 'react'
import IRIBadge from '@/components/shared/IRIBadge'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import type { ReasonerResult, ReasonerViolation, InferredAxiom } from '@/types/reasoner'

interface ReasonerResultsProps {
  result?: ReasonerResult | null
  isLoading?: boolean
}

const SEVERITY_STYLES: Record<string, { bg: string; color: string }> = {
  error: { bg: 'rgba(248,81,73,0.15)', color: 'var(--color-error)' },
  warning: { bg: 'rgba(210,153,34,0.15)', color: 'var(--color-warning)' },
  info: { bg: 'rgba(121,192,255,0.15)', color: 'var(--color-info)' },
}

function ViolationRow({ v }: { v: ReasonerViolation }) {
  const style = SEVERITY_STYLES[v.severity] ?? SEVERITY_STYLES.info
  return (
    <div
      className="p-3 rounded-lg border flex flex-col gap-2"
      style={{ borderColor: style.color + '40', backgroundColor: style.bg }}
    >
      <div className="flex items-center gap-2">
        <span
          className="text-xs px-1.5 py-0.5 rounded font-semibold uppercase"
          style={{ backgroundColor: style.bg, color: style.color, border: `1px solid ${style.color}` }}
        >
          {v.severity}
        </span>
        <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          {v.violation_type}
        </span>
      </div>
      <p className="text-sm" style={{ color: 'var(--color-text-primary)' }}>{v.message}</p>
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span style={{ color: 'var(--color-text-muted)' }}>Subject:</span>
        <IRIBadge iri={v.subject_iri} />
        {v.predicate_iri && (
          <>
            <span style={{ color: 'var(--color-text-muted)' }}>Predicate:</span>
            <IRIBadge iri={v.predicate_iri} />
          </>
        )}
        {v.object_iri && (
          <>
            <span style={{ color: 'var(--color-text-muted)' }}>Object:</span>
            <IRIBadge iri={v.object_iri} />
          </>
        )}
      </div>
    </div>
  )
}

function AxiomRow({ a }: { a: InferredAxiom }) {
  return (
    <div
      className="p-3 rounded-lg border flex flex-col gap-2"
      style={{
        borderColor: 'var(--color-border)',
        backgroundColor: 'var(--color-bg-surface)',
      }}
    >
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <IRIBadge iri={a.subject_iri} />
        <span style={{ color: 'var(--color-text-muted)' }}>→</span>
        <IRIBadge iri={a.predicate_iri} />
        <span style={{ color: 'var(--color-text-muted)' }}>→</span>
        <IRIBadge iri={a.object_iri} />
      </div>
      <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
        <span>Rule: <span style={{ color: 'var(--color-info)' }}>{a.inference_rule}</span></span>
        <span>Confidence: <span style={{ color: 'var(--color-success)' }}>{(a.confidence * 100).toFixed(0)}%</span></span>
      </div>
    </div>
  )
}

export default function ReasonerResults({ result, isLoading = false }: ReasonerResultsProps) {
  const [tab, setTab] = useState<'violations' | 'inferred'>('violations')

  if (isLoading || result?.status === 'pending' || result?.status === 'running') {
    return (
      <div className="flex items-center justify-center py-12 gap-3">
        <LoadingSpinner size="md" />
        <span style={{ color: 'var(--color-text-secondary)' }}>
          {result?.status === 'running' ? 'Reasoner is running...' : 'Running reasoner...'}
        </span>
      </div>
    )
  }

  if (!result) return null

  if (result.status === 'failed') {
    return (
      <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}>
        <p className="font-medium" style={{ color: 'var(--color-error)' }}>Reasoner failed</p>
        {result.error && <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>{result.error}</p>}
      </div>
    )
  }

  const violations = result.violations ?? []
  const axioms = result.inferred_axioms ?? []

  return (
    <div className="flex flex-col gap-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-lg border text-center"
          style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}>
          <div className="text-2xl font-bold" style={{ color: violations.length > 0 ? 'var(--color-error)' : 'var(--color-success)' }}>
            {result.violation_count ?? violations.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>Violations</div>
        </div>
        <div className="p-3 rounded-lg border text-center"
          style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}>
          <div className="text-2xl font-bold" style={{ color: 'var(--color-info)' }}>
            {result.inferred_count ?? axioms.length}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>Inferred Axioms</div>
        </div>
        <div className="p-3 rounded-lg border text-center"
          style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-surface)' }}>
          <div className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            {result.elapsed_seconds ? `${result.elapsed_seconds.toFixed(1)}s` : '—'}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>Duration</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b" style={{ borderColor: 'var(--color-border)' }}>
        <button
          className="px-4 py-2 text-sm border-b-2 transition-colors"
          style={{
            borderColor: tab === 'violations' ? 'var(--color-primary)' : 'transparent',
            color: tab === 'violations' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }}
          onClick={() => setTab('violations')}
        >
          Violations ({violations.length})
        </button>
        <button
          className="px-4 py-2 text-sm border-b-2 transition-colors"
          style={{
            borderColor: tab === 'inferred' ? 'var(--color-primary)' : 'transparent',
            color: tab === 'inferred' ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          }}
          onClick={() => setTab('inferred')}
        >
          Inferred Axioms ({axioms.length})
        </button>
      </div>

      {/* Tab content */}
      <div className="flex flex-col gap-2">
        {tab === 'violations' && (
          violations.length === 0
            ? <p className="text-sm py-4 text-center" style={{ color: 'var(--color-success)' }}>No violations found — ontology is consistent!</p>
            : violations.map((v, i) => <ViolationRow key={i} v={v} />)
        )}
        {tab === 'inferred' && (
          axioms.length === 0
            ? <p className="text-sm py-4 text-center" style={{ color: 'var(--color-text-muted)' }}>No inferred axioms</p>
            : axioms.map((a, i) => <AxiomRow key={i} a={a} />)
        )}
      </div>
    </div>
  )
}
