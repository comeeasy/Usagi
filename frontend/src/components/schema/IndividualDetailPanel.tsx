/**
 * IndividualDetailPanel — Schema 탭 Individual 상세
 *
 * [Detail] [Provenance]
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getIndividual } from '@/api/entities'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import IRIBadge from '@/components/shared/IRIBadge'
import ProvenancePanel from '@/components/provenance/ProvenancePanel'

function localName(iri: string): string {
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}

type Tab = 'detail' | 'provenance'

interface Props {
  ontologyId: string
  dataset: string
  individualIri: string
  onEdit?: () => void
  onDelete?: () => void
}

export default function IndividualDetailPanel({ ontologyId, dataset, individualIri, onEdit, onDelete }: Props) {
  const [tab, setTab] = useState<Tab>('detail')

  const query = useQuery({
    queryKey: ['individual', ontologyId, dataset, individualIri],
    queryFn: () => getIndividual(ontologyId, individualIri, dataset),
    enabled: !!individualIri,
  })

  const ind = query.data

  return (
    <div
      data-testid="schema-individual-detail-panel"
      className="flex flex-col h-full overflow-hidden"
    >
      {/* Header */}
      <div
        className="flex items-center gap-1 px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex-1">
          {query.isLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <h2 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              {ind?.label || localName(individualIri)}
            </h2>
          )}
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>owl:NamedIndividual</p>
        </div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="px-2 py-1 text-xs rounded hover:opacity-80"
            style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}
          >
            Edit
          </button>
        )}
        {onDelete && (
          <button
            onClick={onDelete}
            className="px-2 py-1 text-xs rounded hover:opacity-80"
            style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-error)' }}
          >
            Delete
          </button>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex border-b flex-shrink-0" style={{ borderColor: 'var(--color-border)' }}>
        {(['detail', 'provenance'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-2 text-xs font-medium border-b-2 transition-colors capitalize"
            style={{
              borderBottomColor: tab === t ? 'var(--color-primary)' : 'transparent',
              color: tab === t ? 'var(--color-primary)' : 'var(--color-text-secondary)',
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {query.isLoading && (
          <div className="flex justify-center py-6"><LoadingSpinner size="sm" /></div>
        )}

        {tab === 'detail' && ind && (
          <div className="flex flex-col gap-4">
            {/* IRI */}
            <div>
              <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>IRI</label>
              <IRIBadge iri={ind.iri} showCopy />
            </div>

            {/* Types */}
            {ind.types.length > 0 && (
              <div>
                <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Types</label>
                <div className="flex flex-wrap gap-1">
                  {ind.types.map((t) => (
                    <IRIBadge key={t} iri={t} />
                  ))}
                </div>
              </div>
            )}

            {/* Data Property values */}
            {ind.data_property_values.length > 0 && (
              <div>
                <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                  Data Properties
                </label>
                <div className="flex flex-col gap-1">
                  {ind.data_property_values.map((dpv, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs py-1 border-b"
                      style={{ borderColor: 'var(--color-border)' }}
                    >
                      <span
                        className="font-mono truncate"
                        style={{ color: 'var(--color-warning)', maxWidth: '45%' }}
                        title={dpv.property_iri}
                      >
                        {localName(dpv.property_iri)}
                      </span>
                      <span style={{ color: 'var(--color-text-muted)' }}>:</span>
                      <span style={{ color: 'var(--color-text-primary)' }}>{String(dpv.value)}</span>
                      {dpv.datatype && (
                        <span className="ml-auto font-mono" style={{ color: 'var(--color-text-muted)' }}>
                          {localName(dpv.datatype)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Object Property values */}
            {ind.object_property_values.length > 0 && (
              <div>
                <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>
                  Object Properties
                </label>
                <div className="flex flex-col gap-1">
                  {ind.object_property_values.map((opv, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs py-1 border-b"
                      style={{ borderColor: 'var(--color-border)' }}
                    >
                      <span
                        className="font-mono truncate"
                        style={{ color: '#A371F7', maxWidth: '35%' }}
                        title={opv.property_iri}
                      >
                        {localName(opv.property_iri)}
                      </span>
                      <span style={{ color: 'var(--color-text-muted)' }}>→</span>
                      <span
                        className="font-mono truncate"
                        style={{ color: 'var(--color-info)' }}
                        title={opv.target_iri}
                      >
                        {localName(opv.target_iri)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {ind.types.length === 0 &&
              ind.data_property_values.length === 0 &&
              ind.object_property_values.length === 0 && (
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>No additional properties.</p>
              )}
          </div>
        )}

        {tab === 'provenance' && (
          <ProvenancePanel records={ind?.provenance ?? []} />
        )}
      </div>
    </div>
  )
}
