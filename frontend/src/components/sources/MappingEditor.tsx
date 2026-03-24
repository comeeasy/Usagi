import { Plus, X, Upload } from 'lucide-react'
import type { PropertyMapping } from '@/types/source'

interface MappingEditorProps {
  mappings?: PropertyMapping[]
  onChange?: (mappings: PropertyMapping[]) => void
  onImportR2RML?: (turtle: string) => void
}

const PROPERTY_TYPES = ['data', 'object'] as const
const XSD_DATATYPES = [
  '', 'xsd:string', 'xsd:integer', 'xsd:decimal', 'xsd:boolean',
  'xsd:date', 'xsd:dateTime', 'xsd:anyURI',
]

export default function MappingEditor({ mappings = [], onChange, onImportR2RML }: MappingEditorProps) {
  const inputStyle = {
    backgroundColor: 'var(--color-bg-base)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const addMapping = () => {
    const updated: PropertyMapping[] = [
      ...mappings,
      { source_field: '', property_iri: '', property_type: 'data' },
    ]
    onChange?.(updated)
  }

  const removeMapping = (i: number) => {
    onChange?.(mappings.filter((_, j) => j !== i))
  }

  const updateMapping = (i: number, field: keyof PropertyMapping, value: string) => {
    const updated = [...mappings]
    updated[i] = { ...updated[i], [field]: value }
    onChange?.(updated)
  }

  const handleR2RMLImport = () => {
    const turtle = prompt('Paste R2RML/Turtle content:')
    if (turtle) onImportR2RML?.(turtle)
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Property Mappings ({mappings.length})
        </span>
        <div className="flex gap-2">
          {onImportR2RML && (
            <button
              type="button"
              onClick={handleR2RMLImport}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded border hover:opacity-80"
              style={{
                backgroundColor: 'var(--color-bg-elevated)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
            >
              <Upload size={11} />
              Import R2RML
            </button>
          )}
          <button
            type="button"
            onClick={addMapping}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded border hover:opacity-80"
            style={{
              backgroundColor: 'var(--color-primary)',
              borderColor: 'var(--color-primary)',
              color: '#fff',
            }}
          >
            <Plus size={11} />
            Add Mapping
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--color-border)' }}>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr style={{ backgroundColor: 'var(--color-bg-surface)' }}>
              {['Source Field', 'Property IRI', 'Type', 'Datatype', 'Transform', ''].map((h) => (
                <th key={h} className="px-2 py-1.5 text-left border-b" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-muted)' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {mappings.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-center" style={{ color: 'var(--color-text-muted)' }}>
                  No mappings configured. Click "Add Mapping" to start.
                </td>
              </tr>
            ) : (
              mappings.map((m, i) => (
                <tr key={i} className="border-b" style={{ borderColor: 'var(--color-border)' }}>
                  <td className="px-2 py-1">
                    <input
                      type="text"
                      value={m.source_field}
                      onChange={(e) => updateMapping(i, 'source_field', e.target.value)}
                      placeholder="field_name"
                      className="w-full px-2 py-1 rounded border focus:outline-none font-mono"
                      style={inputStyle}
                    />
                  </td>
                  <td className="px-2 py-1">
                    <input
                      type="text"
                      value={m.property_iri}
                      onChange={(e) => updateMapping(i, 'property_iri', e.target.value)}
                      placeholder="https://example.org/prop"
                      className="w-full px-2 py-1 rounded border focus:outline-none font-mono"
                      style={inputStyle}
                    />
                  </td>
                  <td className="px-2 py-1">
                    <select
                      value={m.property_type}
                      onChange={(e) => updateMapping(i, 'property_type', e.target.value)}
                      className="px-2 py-1 rounded border"
                      style={inputStyle}
                    >
                      {PROPERTY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td className="px-2 py-1">
                    <select
                      value={m.datatype ?? ''}
                      onChange={(e) => updateMapping(i, 'datatype', e.target.value)}
                      className="px-2 py-1 rounded border"
                      style={inputStyle}
                      disabled={m.property_type === 'object'}
                    >
                      {XSD_DATATYPES.map((t) => <option key={t} value={t}>{t || '(auto)'}</option>)}
                    </select>
                  </td>
                  <td className="px-2 py-1">
                    <input
                      type="text"
                      value={m.transform ?? ''}
                      onChange={(e) => updateMapping(i, 'transform', e.target.value)}
                      placeholder="e.g. upper()"
                      className="w-full px-2 py-1 rounded border focus:outline-none"
                      style={inputStyle}
                    />
                  </td>
                  <td className="px-2 py-1">
                    <button
                      type="button"
                      onClick={() => removeMapping(i)}
                      className="p-1 rounded hover:opacity-80"
                      style={{ color: 'var(--color-error)' }}
                    >
                      <X size={12} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
