/**
 * EntityRightPanel — Entities / Relations 탭 하단 패널
 *
 * 레이아웃 (탭 없음):
 *   상단 좌: SubGraph (EntityGraphPanel, flex-1)
 *   상단 우: Detail (detailContent prop, w-80)
 *   하단:    Reasoner 섹션 (헤더 바 + 토글 시 Config + Results 확장)
 */
import { useState } from 'react'
import { X, Brain, Play, ChevronDown, ChevronUp } from 'lucide-react'
import EntityGraphPanel from './EntityGraphPanel'
import ReasonerResults from '@/components/reasoner/ReasonerResults'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useReasoner } from '@/hooks/useReasoner'

interface EntityRightPanelProps {
  ontologyId: string
  selectedIri: string | null
  graphIris: string[]
  onRemoveIri: (iri: string) => void
  onClose: () => void
  detailContent?: React.ReactNode
  /** true이면 하단 고정 패널로 렌더링 */
  bottomLayout?: boolean
}

export default function EntityRightPanel({
  ontologyId,
  selectedIri: _selectedIri,
  graphIris,
  onRemoveIri,
  onClose,
  detailContent,
  bottomLayout = false,
}: EntityRightPanelProps) {
  const [reasonerOpen, setReasonerOpen] = useState(false)
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
      subgraph_entity_iris: graphIris.length ? graphIris : undefined,
      include_inferences: includeInferences,
      check_consistency: checkConsistency,
      reasoner_profile: profile,
    })
  }

  return (
    <aside
      className={
        bottomLayout
          ? 'flex flex-col border-t overflow-hidden flex-shrink-0'
          : 'w-[680px] flex flex-col border-l overflow-hidden flex-shrink-0'
      }
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* 상단: Graph (좌) + Detail (우) — 고정 높이로 graph canvas 보장 */}
      <div className="flex overflow-hidden flex-shrink-0" style={{ height: '288px' }}>
        {/* SubGraph */}
        <div className="flex-1 overflow-hidden">
          <EntityGraphPanel
            ontologyId={ontologyId}
            entityIris={graphIris}
            onRemoveIri={onRemoveIri}
          />
        </div>

        {/* Detail */}
        {detailContent && (
          <div
            className="w-80 flex-shrink-0 overflow-y-auto border-l"
            style={{ borderColor: 'var(--color-border)' }}
          >
            {detailContent}
          </div>
        )}
      </div>

      {/* 하단: Reasoner 섹션 */}
      <div className="flex flex-col flex-shrink-0 border-t" style={{ borderColor: 'var(--color-border)' }}>
        {/* Reasoner 헤더 바 */}
        <div className="flex items-center gap-2 px-3 py-2">
          <Brain size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
            Reasoner
          </span>
          <button
            onClick={() => setReasonerOpen((v) => !v)}
            className="p-0.5 rounded hover:opacity-60"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {reasonerOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {/* 상태 칩 (결과 요약) */}
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
                {resultQuery.data.result.inferred_axioms.length} inferred ·{' '}
                {resultQuery.data.result.execution_ms} ms
              </span>
            </div>
          )}
          {isRunning && (
            <div className="flex items-center gap-1 ml-1">
              <LoadingSpinner size="sm" />
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Running…</span>
            </div>
          )}

          {/* Close panel */}
          <button
            onClick={onClose}
            className="ml-auto p-1 rounded hover:opacity-60"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <X size={14} />
          </button>
        </div>

        {/* Reasoner 확장 패널 */}
        {reasonerOpen && (
          <div className="flex flex-col border-t" style={{ borderColor: 'var(--color-border)' }}>
            {/* Config row */}
            <div
              className="flex items-center gap-4 px-3 py-2 flex-wrap border-b"
              style={{ borderColor: 'var(--color-border)' }}
            >
              {/* Checkboxes */}
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

              {/* Profile selector */}
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

              {/* Run button */}
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

            {/* Results */}
            <div className="overflow-y-auto p-3" style={{ maxHeight: '320px' }}>
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
          </div>
        )}
      </div>
    </aside>
  )
}
