import { useState } from 'react'
import type { SourceType, BackingSourceCreate, JDBCConfig, APIConfig } from '@/types/source'

interface SourceConfigFormProps {
  initialValues?: Partial<BackingSourceCreate>
  onSubmit?: (values: BackingSourceCreate) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

const SOURCE_TYPES: SourceType[] = ['jdbc', 'api', 'stream', 'file']

export default function SourceConfigForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: SourceConfigFormProps) {
  const [sourceType, setSourceType] = useState<SourceType>(initialValues?.source_type ?? 'jdbc')
  const [name, setName] = useState(initialValues?.name ?? '')
  const [conceptIri, setConceptIri] = useState(initialValues?.concept_iri ?? '')
  const [iriTemplate, setIriTemplate] = useState(initialValues?.iri_template ?? '')

  // JDBC config
  const [jdbcUrl, setJdbcUrl] = useState((initialValues?.jdbc_config as JDBCConfig)?.url ?? '')
  const [jdbcDriver, setJdbcDriver] = useState((initialValues?.jdbc_config as JDBCConfig)?.driver ?? '')
  const [jdbcUsername, setJdbcUsername] = useState((initialValues?.jdbc_config as JDBCConfig)?.username ?? '')
  const [jdbcPassword, setJdbcPassword] = useState((initialValues?.jdbc_config as JDBCConfig)?.password ?? '')
  const [jdbcQuery, setJdbcQuery] = useState((initialValues?.jdbc_config as JDBCConfig)?.query ?? '')
  const [jdbcBatchSize, setJdbcBatchSize] = useState((initialValues?.jdbc_config as JDBCConfig)?.batch_size ?? 1000)

  // API config
  const [apiEndpoint, setApiEndpoint] = useState((initialValues?.api_config as APIConfig)?.endpoint ?? '')
  const [apiMethod, setApiMethod] = useState<'GET' | 'POST'>((initialValues?.api_config as APIConfig)?.method ?? 'GET')
  const [apiAuthType, setApiAuthType] = useState<string>((initialValues?.api_config as APIConfig)?.auth_type ?? 'none')
  const [apiAuthToken, setApiAuthToken] = useState((initialValues?.api_config as APIConfig)?.auth_token ?? '')
  const [apiRecordsPath, setApiRecordsPath] = useState((initialValues?.api_config as APIConfig)?.records_path ?? '')

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const labelStyle = { color: 'var(--color-text-secondary)' }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: BackingSourceCreate = {
      name,
      source_type: sourceType,
      concept_iri: conceptIri,
      iri_template: iriTemplate,
    }

    if (sourceType === 'jdbc') {
      data.jdbc_config = {
        url: jdbcUrl,
        driver: jdbcDriver,
        username: jdbcUsername,
        password: jdbcPassword,
        query: jdbcQuery,
        batch_size: jdbcBatchSize,
      }
    } else if (sourceType === 'api') {
      data.api_config = {
        endpoint: apiEndpoint,
        method: apiMethod,
        headers: {},
        params: {},
        auth_type: apiAuthType as APIConfig['auth_type'],
        auth_token: apiAuthToken,
        pagination_type: 'none',
        records_path: apiRecordsPath,
      }
    }

    onSubmit?.(data)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Source type tabs */}
      <div className="flex border rounded overflow-hidden" style={{ borderColor: 'var(--color-border)' }}>
        {SOURCE_TYPES.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setSourceType(t)}
            className="flex-1 py-1.5 text-xs uppercase font-medium transition-colors"
            style={{
              backgroundColor: sourceType === t ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
              color: sourceType === t ? '#fff' : 'var(--color-text-secondary)',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Source Name *</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required
          placeholder="My Database Source" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Concept IRI *</label>
        <input type="text" value={conceptIri} onChange={(e) => setConceptIri(e.target.value)} required
          placeholder="https://example.org/MyClass" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>IRI Template *</label>
        <input type="text" value={iriTemplate} onChange={(e) => setIriTemplate(e.target.value)} required
          placeholder="https://example.org/MyClass/{id}" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>Use {'{field_name}'} for field substitution</p>
      </div>

      {/* JDBC config */}
      {sourceType === 'jdbc' && (
        <div className="flex flex-col gap-3 p-3 rounded border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-elevated)' }}>
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>JDBC Configuration</p>
          <div>
            <label className="block text-xs mb-1" style={labelStyle}>JDBC URL</label>
            <input type="text" value={jdbcUrl} onChange={(e) => setJdbcUrl(e.target.value)}
              placeholder="jdbc:postgresql://localhost:5432/mydb" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Driver</label>
              <input type="text" value={jdbcDriver} onChange={(e) => setJdbcDriver(e.target.value)}
                placeholder="org.postgresql.Driver" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Batch Size</label>
              <input type="number" value={jdbcBatchSize} onChange={(e) => setJdbcBatchSize(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Username</label>
              <input type="text" value={jdbcUsername} onChange={(e) => setJdbcUsername(e.target.value)}
                className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Password</label>
              <input type="password" value={jdbcPassword} onChange={(e) => setJdbcPassword(e.target.value)}
                className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
            </div>
          </div>
          <div>
            <label className="block text-xs mb-1" style={labelStyle}>SQL Query</label>
            <textarea value={jdbcQuery} onChange={(e) => setJdbcQuery(e.target.value)} rows={3}
              placeholder="SELECT * FROM my_table" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono resize-none" style={inputStyle} />
          </div>
        </div>
      )}

      {/* API config */}
      {sourceType === 'api' && (
        <div className="flex flex-col gap-3 p-3 rounded border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-elevated)' }}>
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>API Configuration</p>
          <div>
            <label className="block text-xs mb-1" style={labelStyle}>Endpoint URL</label>
            <input type="text" value={apiEndpoint} onChange={(e) => setApiEndpoint(e.target.value)}
              placeholder="https://api.example.org/data" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Method</label>
              <select value={apiMethod} onChange={(e) => setApiMethod(e.target.value as 'GET' | 'POST')}
                className="w-full px-3 py-1.5 rounded border text-sm" style={inputStyle}>
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
            </div>
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Auth Type</label>
              <select value={apiAuthType} onChange={(e) => setApiAuthType(e.target.value)}
                className="w-full px-3 py-1.5 rounded border text-sm" style={inputStyle}>
                {['none', 'bearer', 'basic', 'api_key'].map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          </div>
          {apiAuthType !== 'none' && (
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Auth Token</label>
              <input type="password" value={apiAuthToken} onChange={(e) => setApiAuthToken(e.target.value)}
                className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
            </div>
          )}
          <div>
            <label className="block text-xs mb-1" style={labelStyle}>Records Path (JSONPath)</label>
            <input type="text" value={apiRecordsPath} onChange={(e) => setApiRecordsPath(e.target.value)}
              placeholder="$.data.items" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
          </div>
        </div>
      )}

      {(sourceType === 'stream' || sourceType === 'file') && (
        <div className="p-3 rounded border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-elevated)' }}>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            {sourceType === 'stream' ? 'Stream' : 'File'} configuration will be available in a future update.
          </p>
        </div>
      )}

      <div className="flex gap-2 pt-2">
        <button type="submit" className="px-4 py-1.5 rounded text-sm font-medium hover:opacity-80"
          style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
          {mode === 'create' ? 'Create Source' : 'Save Changes'}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="px-4 py-1.5 rounded text-sm hover:opacity-80"
            style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
