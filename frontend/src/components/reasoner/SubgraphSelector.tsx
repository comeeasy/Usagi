import IRIBadge from '@/components/shared/IRIBadge'

const PROFILES = ['EL', 'RL', 'QL', 'FULL'] as const

interface SubgraphSelectorProps {
  availableGraphs?: string[]
  selectedGraphs?: string[]
  onSelectionChange?: (graphs: string[]) => void
  profile?: string
  onProfileChange?: (profile: string) => void
}

export default function SubgraphSelector({
  availableGraphs = [],
  selectedGraphs = [],
  onSelectionChange,
  profile = 'EL',
  onProfileChange,
}: SubgraphSelectorProps) {
  const allSelected = selectedGraphs.length === 0

  const toggleGraph = (iri: string) => {
    if (selectedGraphs.includes(iri)) {
      onSelectionChange?.(selectedGraphs.filter((g) => g !== iri))
    } else {
      onSelectionChange?.([...selectedGraphs, iri])
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Reasoner profile */}
      <div>
        <label className="block text-xs mb-2 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Reasoner Profile
        </label>
        <div className="flex gap-2">
          {PROFILES.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => onProfileChange?.(p)}
              className="px-3 py-1.5 rounded border text-sm font-medium transition-all"
              style={{
                backgroundColor: profile === p ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                borderColor: profile === p ? 'var(--color-primary)' : 'var(--color-border)',
                color: profile === p ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              {p}
            </button>
          ))}
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
          {profile === 'EL' && 'EL: Description Logic EL — fast, polynomial complexity'}
          {profile === 'RL' && 'RL: Description Logic RL — rule-based reasoning'}
          {profile === 'QL' && 'QL: Description Logic QL — query answering'}
          {profile === 'FULL' && 'FULL: Complete OWL 2 — most expressive, may be slow'}
        </p>
      </div>

      {/* Subgraph scope */}
      <div>
        <label className="block text-xs mb-2 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Subgraph Scope
        </label>

        <label className="flex items-center gap-2 text-sm cursor-pointer mb-2">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={(e) => {
              if (e.target.checked) onSelectionChange?.([])
            }}
            className="w-3.5 h-3.5"
          />
          <span style={{ color: allSelected ? 'var(--color-primary)' : 'var(--color-text-primary)' }}>
            Entire Ontology
          </span>
        </label>

        {availableGraphs.length > 0 && (
          <div className="flex flex-col gap-1.5 ml-2 mt-2">
            {availableGraphs.map((iri) => (
              <label key={iri} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedGraphs.includes(iri)}
                  onChange={() => toggleGraph(iri)}
                  className="w-3.5 h-3.5"
                />
                <IRIBadge iri={iri} />
              </label>
            ))}
          </div>
        )}

        {availableGraphs.length === 0 && !allSelected && (
          <p className="text-xs ml-2" style={{ color: 'var(--color-text-muted)' }}>
            No named graphs available
          </p>
        )}
      </div>
    </div>
  )
}
