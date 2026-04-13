/**
 * SubgraphSelector — Reasoner용 서브그래프 범위 설정
 *
 * SchemaEntityPicker / SchemaRelationPicker 를 통해
 * 스키마에서 seed entity / allowed relation 을 선택한다.
 */
import { X, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import IRIBadge from '@/components/shared/IRIBadge'
import SchemaEntityPicker from './SchemaEntityPicker'
import SchemaRelationPicker from './SchemaRelationPicker'

const PROFILES = ['OWL_DL', 'OWL_EL', 'OWL_RL', 'OWL_QL'] as const

interface SubgraphSelectorProps {
  ontologyId: string
  dataset?: string

  /** Reasoner 프로파일 */
  profile?: string
  onProfileChange?: (profile: string) => void

  /** 선택된 entity IRI 목록 */
  selectedEntities?: string[]
  onEntitiesChange?: (iris: string[]) => void

  /** 선택된 relation type IRI 목록 */
  selectedRelations?: string[]
  onRelationsChange?: (iris: string[]) => void
}

export default function SubgraphSelector({
  ontologyId,
  dataset,
  profile = 'OWL_DL',
  onProfileChange,
  selectedEntities = [],
  onEntitiesChange,
  selectedRelations = [],
  onRelationsChange,
}: SubgraphSelectorProps) {
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const addEntity    = (iri: string) => onEntitiesChange?.([...selectedEntities, iri])
  const removeEntity = (iri: string) => onEntitiesChange?.(selectedEntities.filter((e) => e !== iri))

  const addRelation    = (iri: string) => onRelationsChange?.([...selectedRelations, iri])
  const removeRelation = (iri: string) => onRelationsChange?.(selectedRelations.filter((r) => r !== iri))

  return (
    <div className="flex flex-col gap-4">

      {/* ── Reasoner Profile ── */}
      <div>
        <label className="block text-xs mb-2 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Reasoner Profile
        </label>
        <div className="flex gap-1.5 flex-wrap">
          {PROFILES.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => onProfileChange?.(p)}
              className="px-2.5 py-1 rounded border text-xs font-medium transition-all"
              style={{
                backgroundColor: profile === p ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                borderColor:     profile === p ? 'var(--color-primary)' : 'var(--color-border)',
                color:           profile === p ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              {p}
            </button>
          ))}
        </div>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
          {profile === 'OWL_DL' && 'OWL_DL: complete OWL 2 (HermiT), may be slow'}
          {profile === 'OWL_EL' && 'OWL_EL: fast, polynomial complexity (Pellet)'}
          {profile === 'OWL_RL' && 'OWL_RL: rule-based reasoning (SPARQL)'}
          {profile === 'OWL_QL' && 'OWL_QL: query answering (SPARQL)'}
        </p>
      </div>

      {/* ── Seed Entities ── */}
      <div>
        <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Seed Entities
          <span className="ml-1 font-normal" style={{ color: 'var(--color-text-muted)' }}>
            ({selectedEntities.length === 0 ? 'all' : `${selectedEntities.length} selected`})
          </span>
        </label>

        <SchemaEntityPicker
          ontologyId={ontologyId}
          dataset={dataset}
          selectedIris={selectedEntities}
          onAdd={addEntity}
          onRemove={removeEntity}
        />

        {selectedEntities.length > 0 && (
          <div className="flex flex-col gap-1 mt-2">
            {selectedEntities.map((iri) => (
              <div
                key={iri}
                className="flex items-center justify-between gap-1 px-2 py-1 rounded"
                style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}
              >
                <IRIBadge iri={iri} />
                <button
                  onClick={() => removeEntity(iri)}
                  className="flex-shrink-0 p-0.5 rounded hover:opacity-60"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Empty = entire ontology.
        </p>
      </div>

      {/* ── Relation Types ── */}
      <div>
        <label className="block text-xs mb-1.5 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Allowed Relations
          <span className="ml-1 font-normal" style={{ color: 'var(--color-text-muted)' }}>
            ({selectedRelations.length === 0 ? 'all' : `${selectedRelations.length} selected`})
          </span>
        </label>

        <SchemaRelationPicker
          ontologyId={ontologyId}
          dataset={dataset}
          selectedIris={selectedRelations}
          onAdd={addRelation}
          onRemove={removeRelation}
        />

        {selectedRelations.length > 0 && (
          <div className="flex flex-col gap-1 mt-2">
            {selectedRelations.map((iri) => (
              <div
                key={iri}
                className="flex items-center justify-between gap-1 px-2 py-1 rounded"
                style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}
              >
                <IRIBadge iri={iri} />
                <button
                  onClick={() => removeRelation(iri)}
                  className="flex-shrink-0 p-0.5 rounded hover:opacity-60"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Empty = all relation types allowed.
        </p>
      </div>

      {/* ── Advanced Options ── */}
      <div>
        <button
          type="button"
          onClick={() => setAdvancedOpen((v) => !v)}
          className="flex items-center gap-1 text-xs hover:opacity-70"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {advancedOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          Advanced options
        </button>
      </div>
    </div>
  )
}
