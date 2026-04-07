/**
 * EntityRightPanel — Entities / Relations 탭의 우측 패널
 *
 * 탭:
 *   Detail   — entity/property 상세 정보
 *   Graph    — 선택된 entities 그래프 (multi-IRI chips + canvas)
 *   Reasoner — 현재 그래프 entity들로 즉시 추론 실행
 */
import { useState } from 'react'
import { X, Brain, Play, CheckCircle, AlertTriangle } from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import EntityGraphPanel from './EntityGraphPanel'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { runReasoner, getReasonerResult } from '@/api/reasoner'
import { useDataset } from '@/contexts/DatasetContext'
import type { ReasonerResultData } from '@/types/reasoner'

type PanelTab = 'detail' | 'graph' | 'reasoner'

interface EntityRightPanelProps {
  ontologyId: string
  /** Currently focused IRI (for detail display) */
  selectedIri: string | null
  /** All IRIs pinned in the graph */
  graphIris: string[]
  onRemoveIri: (iri: string) => void
  onClose: () => void
  /** Slot for the detail content (rendered by parent) */
  detailContent?: React.ReactNode
}

export default function EntityRightPanel({
  ontologyId,
  selectedIri,
  graphIris,
  onRemoveIri,
  onClose,
  detailContent,
}: EntityRightPanelProps) {
  const { dataset } = useDataset()
  const [tab, setTab] = useState<PanelTab>('detail')
  const [jobId, setJobId] = useState<string | null>(null)

  // Reasoner quick-run
  const runMutation = useMutation({
    mutationFn: () =>
      runReasoner(
        ontologyId,
        { subgraph_entity_iris: graphIris.length ? graphIris : undefined },
        dataset,
      ),
    onSuccess: (job) => setJobId(job.job_id),
  })

  const resultQuery = useQuery({
    queryKey: ['reasoner-inline', jobId],
    queryFn: () => getReasonerResult(ontologyId, jobId!),
    enabled: !!jobId,
    refetchInterval: (q) => {
      const s = q.state.data?.status
      return s === 'completed' || s === 'failed' ? false : 1000
    },
  })

  const isRunning =
    runMutation.isPending ||
    resultQuery.data?.status === 'pending' ||
    resultQuery.data?.status === 'running'

  const resultData: ReasonerResultData | undefined = resultQuery.data?.result

  return (
    <aside
      className="w-96 flex flex-col border-l overflow-hidden flex-shrink-0"
      style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
    >
      {/* Tabs header */}
      <div
        className="flex items-center border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        {(['detail', 'graph', 'reasoner'] as PanelTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-3 py-2 text-xs font-medium border-b-2 transition-colors capitalize"
            style={{
              borderColor: tab === t ? 'var(--color-primary)' : 'transparent',
              color: tab === t ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            }}
          >
            {t === 'reasoner' ? <Brain size={12} className="inline mr-1" /> : null}
            {t}
          </button>
        ))}
        <button
          onClick={onClose}
          className="ml-auto mr-2 p-1 rounded hover:opacity-60"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <X size={14} />
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Detail */}
        {tab === 'detail' && (
          <div className="flex-1 overflow-y-auto">
            {detailContent ?? (
              <div className="flex items-center justify-center h-full text-sm"
                   style={{ color: 'var(--color-text-muted)' }}>
                {selectedIri ? 'Loading…' : 'Select an entity to view details'}
              </div>
            )}
          </div>
        )}

        {/* Graph */}
        {tab === 'graph' && (
          <div className="flex-1 overflow-hidden">
            <EntityGraphPanel
              ontologyId={ontologyId}
              entityIris={graphIris}
              onRemoveIri={onRemoveIri}
            />
          </div>
        )}

        {/* Reasoner */}
        {tab === 'reasoner' && (
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Runs OWL reasoning on the current graph selection
              {graphIris.length > 0 && ` (${graphIris.length} entities)`}.
            </p>

            <button
              onClick={() => { setJobId(null); runMutation.reset(); runMutation.mutate() }}
              disabled={isRunning}
              className="flex items-center justify-center gap-2 py-2 rounded text-xs font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              {isRunning ? <><LoadingSpinner size="sm" /> Running…</> : <><Play size={12} /> Run Reasoner</>}
            </button>

            {runMutation.error && (
              <p className="text-xs" style={{ color: 'var(--color-error)' }}>
                {runMutation.error.message}
              </p>
            )}

            {resultData && (
              <div className="flex flex-col gap-2">
                {/* Consistency */}
                <div className={`flex items-center gap-1.5 text-xs font-medium ${resultData.consistent ? 'text-green-500' : 'text-red-500'}`}>
                  {resultData.consistent
                    ? <><CheckCircle size={12} /> Consistent</>
                    : <><AlertTriangle size={12} /> Inconsistent</>
                  }
                  <span className="font-normal ml-auto" style={{ color: 'var(--color-text-muted)' }}>
                    {resultData.execution_ms} ms
                  </span>
                </div>

                {/* Violations */}
                {resultData.violations.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>
                      Violations ({resultData.violations.length})
                    </p>
                    <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                      {resultData.violations.map((v, i) => (
                        <div key={i} className="text-xs p-2 rounded"
                             style={{ background: 'rgba(248,81,73,0.1)', color: 'var(--color-text-primary)' }}>
                          <span className="font-medium text-red-400">{v.type}</span>
                          <p className="mt-0.5 break-words">{v.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Inferred */}
                {resultData.inferred_axioms.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold mb-1" style={{ color: 'var(--color-text-muted)' }}>
                      Inferred ({resultData.inferred_axioms.length})
                    </p>
                    <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                      {resultData.inferred_axioms.slice(0, 20).map((ax, i) => (
                        <div key={i} className="text-xs p-1.5 rounded font-mono break-all"
                             style={{ background: 'var(--color-bg-elevated)', color: 'var(--color-text-secondary)' }}>
                          {shortIri(ax.subject)} · {shortIri(ax.predicate)} · {shortIri(ax.object)}
                        </div>
                      ))}
                      {resultData.inferred_axioms.length > 20 && (
                        <p className="text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
                          +{resultData.inferred_axioms.length - 20} more
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}

function shortIri(iri: string) {
  if (iri.includes('#')) return iri.split('#').at(-1) ?? iri
  return iri.split('/').at(-1) ?? iri
}
