import { useState } from 'react'
import { useParams } from 'react-router-dom'
import OntologyTabs from '@/components/layout/OntologyTabs'
import SPARQLEditor from '@/components/sparql/SPARQLEditor'
import SPARQLResultsTable from '@/components/sparql/SPARQLResultsTable'
import ErrorBoundary from '@/components/shared/ErrorBoundary'
import { useSPARQL } from '@/hooks/useSPARQL'

const DEFAULT_QUERY = `PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label WHERE {
  ?class a owl:Class .
  OPTIONAL { ?class rdfs:label ?label }
}
LIMIT 50`

export default function SPARQLPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const [query, setQuery] = useState(DEFAULT_QUERY)
  const sparqlMutation = useSPARQL(ontologyId)

  const handleExecute = (q: string) => {
    sparqlMutation.mutate(q)
  }

  return (
    <ErrorBoundary>
      <div className="flex flex-col h-full">
        <OntologyTabs />

        <div className="flex flex-col flex-1 overflow-hidden p-4 gap-4">
          {/* Header */}
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              SPARQL Query
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
              Query the ontology using SPARQL 1.1
            </p>
          </div>

          {/* Editor */}
          <SPARQLEditor
            value={query}
            onChange={setQuery}
            onExecute={handleExecute}
          />

          {/* Error */}
          {sparqlMutation.error && (
            <div
              className="p-3 rounded-lg border text-sm"
              style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
            >
              Query error: {sparqlMutation.error.message}
            </div>
          )}

          {/* Results */}
          <div className="flex-1 overflow-auto">
            <SPARQLResultsTable
              results={sparqlMutation.data}
              isLoading={sparqlMutation.isPending}
            />
          </div>
        </div>
      </div>
    </ErrorBoundary>
  )
}
