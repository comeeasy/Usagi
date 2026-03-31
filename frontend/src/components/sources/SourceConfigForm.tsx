import { useState } from 'react'
import type { SourceType, BackingSourceCreate, JDBCConfig, APIConfig, CSVConfig } from '@/types/source'
import IRISearchInput from '@/components/shared/IRISearchInput'

interface SourceConfigFormProps {
  initialValues?: Partial<BackingSourceCreate>
  onSubmit?: (values: BackingSourceCreate) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

const SOURCE_TYPES: { value: SourceType; label: string }[] = [
  { value: 'jdbc', label: 'JDBC' },
  { value: 'api', label: 'API' },
  { value: 'stream', label: 'Stream' },
  { value: 'csv-file', label: 'CSV' },
]

export default function SourceConfigForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: SourceConfigFormProps) {
  const [sourceType, setSourceType] = useState<SourceType>(initialValues?.source_type ?? 'csv-file')
  const [label, setLabel] = useState(initialValues?.label ?? '')
  const [conceptIri, setConceptIri] = useState(initialValues?.concept_iri ?? '')
  const [iriTemplate, setIriTemplate] = useState(initialValues?.iri_template ?? '')

  // JDBC config
  const [jdbcUrl, setJdbcUrl] = useState((initialValues?.config as JDBCConfig)?.url ?? '')
  const [jdbcDriver, setJdbcDriver] = useState((initialValues?.config as JDBCConfig)?.driver ?? '')
  const [jdbcUsername, setJdbcUsername] = useState((initialValues?.config as JDBCConfig)?.username ?? '')
  const [jdbcPassword, setJdbcPassword] = useState((initialValues?.config as JDBCConfig)?.password ?? '')
  const [jdbcQuery, setJdbcQuery] = useState((initialValues?.config as JDBCConfig)?.query ?? '')
  const [jdbcBatchSize, setJdbcBatchSize] = useState((initialValues?.config as JDBCConfig)?.batch_size ?? 1000)

  // API config
  const [apiEndpoint, setApiEndpoint] = useState((initialValues?.config as APIConfig)?.endpoint ?? '')
  const [apiMethod, setApiMethod] = useState<'GET' | 'POST'>((initialValues?.config as APIConfig)?.method ?? 'GET')
  const [apiAuthType, setApiAuthType] = useState<string>((initialValues?.config as APIConfig)?.auth_type ?? 'none')
  const [apiAuthToken, setApiAuthToken] = useState((initialValues?.config as APIConfig)?.auth_token ?? '')
  const [apiRecordsPath, setApiRecordsPath] = useState((initialValues?.config as APIConfig)?.records_path ?? '')

  // CSV config
  const csvInit = initialValues?.config as CSVConfig | undefined
  const [csvDelimiter, setCsvDelimiter] = useState<CSVConfig['delimiter']>(csvInit?.delimiter ?? ',')
  const [csvHasHeader, setCsvHasHeader] = useState(csvInit?.has_header ?? true)
  const [csvPkField, setCsvPkField] = useState(csvInit?.primary_key_field ?? '')
  const [csvEncoding, setCsvEncoding] = useState<CSVConfig['encoding']>(csvInit?.encoding ?? 'utf-8')
  const [csvSkipRows, setCsvSkipRows] = useState(csvInit?.skip_rows ?? 0)

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }
  const labelStyle = { color: 'var(--color-text-secondary)' }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data: BackingSourceCreate = {
      label,
      source_type: sourceType,
      concept_iri: conceptIri,
      iri_template: iriTemplate,
    }

    if (sourceType === 'jdbc') {
      data.config = {
        url: jdbcUrl, driver: jdbcDriver, username: jdbcUsername,
        password: jdbcPassword, query: jdbcQuery, batch_size: jdbcBatchSize,
      }
    } else if (sourceType === 'api') {
      data.config = {
        endpoint: apiEndpoint, method: apiMethod, headers: {}, params: {},
        auth_type: apiAuthType as APIConfig['auth_type'],
        auth_token: apiAuthToken, pagination_type: 'none', records_path: apiRecordsPath,
      }
    } else if (sourceType === 'csv-file') {
      data.config = {
        delimiter: csvDelimiter, has_header: csvHasHeader,
        primary_key_field: csvPkField, encoding: csvEncoding, skip_rows: csvSkipRows,
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
            key={t.value}
            type="button"
            onClick={() => setSourceType(t.value)}
            className="flex-1 py-1.5 text-xs font-medium transition-colors"
            style={{
              backgroundColor: sourceType === t.value ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
              color: sourceType === t.value ? '#fff' : 'var(--color-text-secondary)',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Source Name *</label>
        <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} required
          placeholder="My CSV Source" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Concept IRI *</label>
        <IRISearchInput
          value={conceptIri}
          onChange={setConceptIri}
          placeholder="Search or enter class IRI…"
          kind="concept"
          required
        />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>IRI Template *</label>
        <input type="text" value={iriTemplate} onChange={(e) => setIriTemplate(e.target.value)} required
          placeholder="https://example.org/MyClass/{id}" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>Use {'{field_name}'} to reference CSV column values</p>
      </div>

      {/* CSV config */}
      {sourceType === 'csv-file' && (
        <div className="flex flex-col gap-3 p-3 rounded border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-elevated)' }}>
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>CSV Configuration</p>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Delimiter</label>
              <select value={csvDelimiter} onChange={(e) => setCsvDelimiter(e.target.value as CSVConfig['delimiter'])}
                className="w-full px-3 py-1.5 rounded border text-sm" style={inputStyle}>
                <option value=",">, (comma)</option>
                <option value=";">; (semicolon)</option>
                <option value={'\t'}>⇥ (tab)</option>
                <option value="|">| (pipe)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Encoding</label>
              <select value={csvEncoding} onChange={(e) => setCsvEncoding(e.target.value as CSVConfig['encoding'])}
                className="w-full px-3 py-1.5 rounded border text-sm" style={inputStyle}>
                <option value="utf-8">UTF-8</option>
                <option value="utf-16">UTF-16</option>
                <option value="latin-1">Latin-1</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs mb-1" style={labelStyle}>Primary Key Column *</label>
            <input type="text" value={csvPkField} onChange={(e) => setCsvPkField(e.target.value)} required
              placeholder="id" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>Column used in IRI template (must match a column name in the CSV)</p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-2">
              <input type="checkbox" id="hasHeader" checked={csvHasHeader} onChange={(e) => setCsvHasHeader(e.target.checked)}
                className="w-3.5 h-3.5" />
              <label htmlFor="hasHeader" className="text-xs cursor-pointer" style={labelStyle}>First row is header</label>
            </div>
            <div>
              <label className="block text-xs mb-1" style={labelStyle}>Skip rows (before header)</label>
              <input type="number" min={0} value={csvSkipRows} onChange={(e) => setCsvSkipRows(Number(e.target.value))}
                className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
            </div>
          </div>
        </div>
      )}

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

      {sourceType === 'stream' && (
        <div className="p-3 rounded border" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-bg-elevated)' }}>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Stream configuration will be available in a future update.</p>
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
