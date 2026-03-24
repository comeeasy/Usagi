import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bug, Play, ArrowLeft } from 'lucide-react'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { apiGet, apiPost } from '@/api/client'

interface ToolDef {
  name: string
  description: string
  endpoint: string
  method: 'GET' | 'POST'
  exampleBody?: string
}

const MCP_TOOLS: ToolDef[] = [
  { name: 'list_ontologies', description: 'List all ontologies', endpoint: '/ontologies', method: 'GET' },
  { name: 'list_concepts', description: 'List concepts for an ontology', endpoint: '/ontologies/{id}/concepts', method: 'GET' },
  { name: 'search_entities', description: 'Search entities by keyword', endpoint: '/ontologies/{id}/search/entities?q=test', method: 'GET' },
  { name: 'execute_sparql', description: 'Execute a SPARQL query', endpoint: '/ontologies/{id}/sparql', method: 'POST', exampleBody: '{"query":"SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"}' },
  { name: 'run_reasoner', description: 'Run the reasoner', endpoint: '/ontologies/{id}/reasoner/run', method: 'POST', exampleBody: '{"reasoner_profile":"EL","check_consistency":true}' },
]

export default function MCPDebugPage() {
  const navigate = useNavigate()
  const [ontologyId, setOntologyId] = useState('')
  const [selectedTool, setSelectedTool] = useState<ToolDef | null>(null)
  const [requestBody, setRequestBody] = useState('')
  const [result, setResult] = useState<unknown>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sseConnected] = useState(false)

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const selectTool = (tool: ToolDef) => {
    setSelectedTool(tool)
    setRequestBody(tool.exampleBody ?? '')
    setResult(null)
    setError(null)
  }

  const executeTool = async () => {
    if (!selectedTool) return
    setIsLoading(true)
    setError(null)
    setResult(null)

    const endpoint = selectedTool.endpoint.replace('{id}', ontologyId || 'ONTOLOGY_ID')
    try {
      let res: unknown
      if (selectedTool.method === 'GET') {
        res = await apiGet(endpoint)
      } else {
        const body = requestBody ? JSON.parse(requestBody) : {}
        res = await apiPost(endpoint, body)
      }
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-bg-base)' }}>
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/')}
            className="p-1.5 rounded hover:opacity-80"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <ArrowLeft size={18} />
          </button>
          <Bug size={20} style={{ color: 'var(--color-primary)' }} />
          <h1 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            MCP Debug
          </h1>
          <div className="ml-auto flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: sseConnected ? 'var(--color-success)' : 'var(--color-error)' }}
            />
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              SSE {sseConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Tool list */}
          <div>
            <div className="mb-3">
              <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                Ontology ID
              </label>
              <input
                type="text"
                value={ontologyId}
                onChange={(e) => setOntologyId(e.target.value)}
                placeholder="ontology-uuid"
                className="w-full px-2 py-1.5 rounded border text-sm focus:outline-none font-mono"
                style={inputStyle}
              />
            </div>

            <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-muted)' }}>
              MCP Tools ({MCP_TOOLS.length})
            </p>
            <div className="flex flex-col gap-1">
              {MCP_TOOLS.map((tool) => (
                <button
                  key={tool.name}
                  onClick={() => selectTool(tool)}
                  className="text-left px-3 py-2 rounded border text-sm transition-all"
                  style={{
                    borderColor: selectedTool?.name === tool.name ? 'var(--color-primary)' : 'var(--color-border)',
                    backgroundColor: selectedTool?.name === tool.name ? 'rgba(47,129,247,0.1)' : 'var(--color-bg-surface)',
                    color: selectedTool?.name === tool.name ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                  }}
                >
                  <p className="font-mono text-xs font-medium">{tool.name}</p>
                  <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--color-text-muted)' }}>
                    {tool.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Tool detail + execute */}
          <div className="flex flex-col gap-3">
            {selectedTool ? (
              <>
                <div
                  className="p-3 rounded-lg border"
                  style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
                >
                  <p className="font-mono text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                    {selectedTool.name}
                  </p>
                  <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                    {selectedTool.description}
                  </p>
                  <p className="font-mono text-xs mt-2" style={{ color: 'var(--color-info)' }}>
                    {selectedTool.method} {selectedTool.endpoint}
                  </p>
                </div>

                {selectedTool.method === 'POST' && (
                  <div>
                    <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                      Request Body (JSON)
                    </label>
                    <textarea
                      value={requestBody}
                      onChange={(e) => setRequestBody(e.target.value)}
                      rows={6}
                      className="w-full px-3 py-2 rounded border text-xs font-mono focus:outline-none resize-none"
                      style={inputStyle}
                    />
                  </div>
                )}

                <button
                  onClick={executeTool}
                  disabled={isLoading}
                  className="flex items-center justify-center gap-2 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
                  style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
                >
                  {isLoading ? <LoadingSpinner size="sm" /> : <Play size={14} />}
                  {isLoading ? 'Executing...' : 'Execute'}
                </button>
              </>
            ) : (
              <div
                className="flex items-center justify-center h-32 rounded-lg border"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
              >
                <p className="text-sm">Select a tool to execute</p>
              </div>
            )}
          </div>

          {/* Result */}
          <div>
            <p className="text-xs font-medium mb-2" style={{ color: 'var(--color-text-muted)' }}>Result</p>

            {error && (
              <div
                className="p-3 rounded-lg border text-sm mb-2"
                style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
              >
                {error}
              </div>
            )}

            {result !== null && (
              <pre
                className="overflow-auto rounded-lg border p-3 text-xs"
                style={{
                  backgroundColor: 'var(--color-bg-elevated)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text-primary)',
                  maxHeight: 500,
                }}
              >
                {JSON.stringify(result, null, 2)}
              </pre>
            )}

            {result === null && !error && !isLoading && (
              <div
                className="flex items-center justify-center h-32 rounded-lg border"
                style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}
              >
                <p className="text-sm">No result yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
