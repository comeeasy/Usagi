import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Brain, Play } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import SubgraphSelector from '@/components/reasoner/SubgraphSelector'
import ReasonerResults from '@/components/reasoner/ReasonerResults'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import { useReasoner } from '@/hooks/useReasoner'

export default function ReasonerPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const { runMutation, resultQuery, jobId } = useReasoner(ontologyId)

  const [selectedEntities, setSelectedEntities] = useState<string[]>([])
  const [selectedRelations, setSelectedRelations] = useState<string[]>([])
  const [profile, setProfile] = useState<'OWL_DL' | 'OWL_EL' | 'OWL_RL' | 'OWL_QL'>('OWL_DL')
  const [includeInferences, setIncludeInferences] = useState(true)
  const [checkConsistency, setCheckConsistency] = useState(true)

  const handleRun = () => {
    runMutation.mutate({
      subgraph_entity_iris: selectedEntities.length > 0 ? selectedEntities : undefined,
      include_inferences: includeInferences,
      check_consistency: checkConsistency,
      reasoner_profile: profile,
    })
  }

  const isRunning = runMutation.isPending ||
    resultQuery.data?.status === 'pending' ||
    resultQuery.data?.status === 'running'

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <OntologyTabs />

        <div className="flex flex-1 overflow-hidden">
          {/* Config sidebar */}
          <div
            className="w-72 flex flex-col p-4 gap-4 border-r overflow-y-auto flex-shrink-0"
            style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
          >
            <div className="flex items-center gap-2">
              <Brain size={16} style={{ color: 'var(--color-primary)' }} />
              <h2 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
                Reasoner Config
              </h2>
            </div>

            <SubgraphSelector
              profile={profile}
              onProfileChange={(p) => setProfile(p as 'OWL_DL' | 'OWL_EL' | 'OWL_RL' | 'OWL_QL')}
              selectedEntities={selectedEntities}
              onEntitiesChange={setSelectedEntities}
              selectedRelations={selectedRelations}
              onRelationsChange={setSelectedRelations}
            />

            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={checkConsistency}
                  onChange={(e) => setCheckConsistency(e.target.checked)}
                  className="w-3.5 h-3.5"
                />
                <span style={{ color: 'var(--color-text-secondary)' }}>Check consistency</span>
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeInferences}
                  onChange={(e) => setIncludeInferences(e.target.checked)}
                  className="w-3.5 h-3.5"
                />
                <span style={{ color: 'var(--color-text-secondary)' }}>Include inferences</span>
              </label>
            </div>

            <button
              onClick={handleRun}
              disabled={isRunning}
              className="flex items-center justify-center gap-2 py-2.5 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50 mt-auto"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              {isRunning ? (
                <>
                  <LoadingSpinner size="sm" />
                  Running...
                </>
              ) : (
                <>
                  <Play size={14} />
                  Run Reasoner
                </>
              )}
            </button>

            {runMutation.error && (
              <p className="text-xs" style={{ color: 'var(--color-error)' }}>
                {runMutation.error.message}
              </p>
            )}

            {jobId && (
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Job: {jobId.slice(0, 8)}...
              </p>
            )}
          </div>

          {/* Results */}
          <div className="flex-1 overflow-y-auto p-4">
            {!jobId && !runMutation.isPending && (
              <div
                className="flex flex-col items-center justify-center h-full gap-4"
                style={{ color: 'var(--color-text-muted)' }}
              >
                <Brain size={48} style={{ opacity: 0.3 }} />
                <p className="text-sm">Configure and run the reasoner to see results</p>
              </div>
            )}

            <ReasonerResults
              result={resultQuery.data ?? null}
              isLoading={isRunning}
            />
          </div>
        </div>
      </div>
    </ErrorBoundary>
  )
}
