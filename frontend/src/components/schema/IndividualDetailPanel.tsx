/**
 * IndividualDetailPanel — Schema 탭 4열: 선택된 Individual 세부 정보
 */
import { useQuery } from '@tanstack/react-query'
import { getIndividual } from '@/api/entities'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import IRIBadge from '@/components/shared/IRIBadge'

function localName(iri: string): string {
  const h = iri.lastIndexOf('#')
  if (h !== -1) return iri.slice(h + 1)
  const s = iri.lastIndexOf('/')
  return s !== -1 ? iri.slice(s + 1) : iri
}

interface Props {
  ontologyId: string
  dataset: string
  individualIri: string
}

export default function IndividualDetailPanel({ ontologyId, dataset, individualIri }: Props) {
  const query = useQuery({
    queryKey: ['individual', ontologyId, dataset, individualIri],
    queryFn: () => getIndividual(ontologyId, individualIri, dataset),
    enabled: !!individualIri,
  })

  return (
    <div
      data-testid="schema-individual-detail-panel"
      className="flex flex-col h-full overflow-hidden border-l"
      style={{ borderColor: 'var(--color-border)' }}
    >
      {/* Header */}
      <div
        className="px-3 py-2 border-b flex-shrink-0"
        style={{
          backgroundColor: 'var(--color-bg-surface)',
          borderColor: 'var(--color-border)',
        }}
      >
        <span className="text-xs font-semibold" style={{ color: 'var(--color-text-secondary)' }}>
          Individual
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {query.isLoading && (
          <div className="flex justify-center py-6">
            <LoadingSpinner size="sm" />
          </div>
        )}

        {query.isSuccess && query.data && (() => {
          const ind = query.data
          return (
            <div className="flex flex-col gap-3">
              {/* Label */}
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                  {ind.label || localName(ind.iri)}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
                  owl:NamedIndividual
                </p>
              </div>

              {/* IRI */}
              <div>
                <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>IRI</label>
                <IRIBadge iri={ind.iri} showCopy />
              </div>

              {/* Types */}
              {ind.types.length > 0 && (
                <div>
                  <label className="text-xs block mb-1" style={{ color: 'var(--color-text-muted)' }}>Types</label>
                  <div className="flex flex-col gap-1">
                    {ind.types.map((t) => (
                      <span
                        key={t}
                        className="font-mono text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: 'var(--color-bg-elevated)',
                          border: '1px solid var(--color-border)',
                          color: 'var(--color-info)',
                        }}
                        title={t}
                      >
                        {localName(t)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Data property values */}
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
                        <span style={{ color: 'var(--color-text-primary)' }}>
                          {String(dpv.value)}
                        </span>
                        {dpv.datatype && (
                          <span className="ml-auto" style={{ color: 'var(--color-text-muted)' }}>
                            {localName(dpv.datatype)}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Object property values */}
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
                          style={{ color: '#A371F7', maxWidth: '45%' }}
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
            </div>
          )
        })()}
      </div>
    </div>
  )
}
