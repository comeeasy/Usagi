import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Upload, Link, BookOpen, CheckCircle } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useMutation } from '@tanstack/react-query'
import { importOntology } from '@/api/ontologies'

type ImportMode = 'file' | 'url' | 'standard'

const STANDARD_ONTOLOGIES = [
  { id: 'schema.org', label: 'Schema.org', url: 'https://schema.org/version/latest/schemaorg-current-https.jsonld', format: 'json-ld' },
  { id: 'foaf', label: 'FOAF', url: 'http://xmlns.com/foaf/spec/index.rdf', format: 'rdf-xml' },
  { id: 'dublin-core', label: 'Dublin Core Terms', url: 'https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.rdf', format: 'rdf-xml' },
  { id: 'skos', label: 'SKOS', url: 'https://www.w3.org/2009/08/skos-reference/skos.rdf', format: 'rdf-xml' },
]

const FORMATS = ['turtle', 'rdf-xml', 'json-ld', 'n-triples', 'n-quads']

export default function ImportPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const [mode, setMode] = useState<ImportMode>('file')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('turtle')
  const [selectedStandard, setSelectedStandard] = useState<string | null>(null)

  const importMutation = useMutation({
    mutationFn: (data: Parameters<typeof importOntology>[1]) => importOntology(ontologyId!, data),
  })

  const handleFileImport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    const content = await file.text()
    importMutation.mutate({ format, content, file_name: file.name })
  }

  const handleUrlImport = (e: React.FormEvent) => {
    e.preventDefault()
    importMutation.mutate({ format, url })
  }

  const handleStandardImport = () => {
    const std = STANDARD_ONTOLOGIES.find((s) => s.id === selectedStandard)
    if (!std) return
    importMutation.mutate({ format: std.format, url: std.url })
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  return (
    <div className="flex flex-col h-full">
      <OntologyTabs />

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <h2 className="text-base font-semibold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          Import Ontology
        </h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
          Import triples from a file, URL, or standard ontology
        </p>

        {/* Mode tabs */}
        <div className="flex gap-2 mb-6">
          {([
            { id: 'file', label: 'File Upload', icon: Upload },
            { id: 'url', label: 'From URL', icon: Link },
            { id: 'standard', label: 'Standard Ontologies', icon: BookOpen },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all"
              style={{
                backgroundColor: mode === id ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                borderColor: mode === id ? 'var(--color-primary)' : 'var(--color-border)',
                color: mode === id ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* Success */}
        {importMutation.isSuccess && (
          <div
            className="flex items-center gap-2 p-3 rounded-lg border mb-4 text-sm"
            style={{ borderColor: 'var(--color-success)', color: 'var(--color-success)', backgroundColor: 'rgba(63,185,80,0.1)' }}
          >
            <CheckCircle size={16} />
            {importMutation.data?.message ?? 'Import successful'}
            {importMutation.data?.triples_imported !== undefined && ` (${importMutation.data.triples_imported} triples)`}
          </div>
        )}

        {/* Error */}
        {importMutation.error && (
          <div
            className="p-3 rounded-lg border mb-4 text-sm"
            style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
          >
            Import failed: {importMutation.error.message}
          </div>
        )}

        {/* File upload */}
        {mode === 'file' && (
          <form onSubmit={handleFileImport} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs mb-2 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
                Format
              </label>
              <select value={format} onChange={(e) => setFormat(e.target.value)}
                className="px-3 py-1.5 rounded border text-sm" style={inputStyle}>
                {FORMATS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <div
              className="border-2 border-dashed rounded-xl p-8 flex flex-col items-center gap-3 cursor-pointer"
              style={{ borderColor: file ? 'var(--color-success)' : 'var(--color-border)' }}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <Upload size={32} style={{ color: 'var(--color-text-muted)' }} />
              <div className="text-center">
                <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                  {file ? file.name : 'Click to select file'}
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                  .ttl, .rdf, .owl, .jsonld, .nt, .nq
                </p>
              </div>
              <input
                id="file-input"
                type="file"
                className="hidden"
                accept=".ttl,.rdf,.owl,.xml,.jsonld,.json,.nt,.nq"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <button
              type="submit"
              disabled={!file || importMutation.isPending}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              {importMutation.isPending && <LoadingSpinner size="sm" />}
              {importMutation.isPending ? 'Importing...' : 'Import File'}
            </button>
          </form>
        )}

        {/* URL import */}
        {mode === 'url' && (
          <form onSubmit={handleUrlImport} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>Format</label>
              <select value={format} onChange={(e) => setFormat(e.target.value)}
                className="px-3 py-1.5 rounded border text-sm" style={inputStyle}>
                {FORMATS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>URL *</label>
              <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} required
                placeholder="https://example.org/ontology.ttl"
                className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
            </div>
            <button type="submit" disabled={!url || importMutation.isPending}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
              {importMutation.isPending && <LoadingSpinner size="sm" />}
              {importMutation.isPending ? 'Importing...' : 'Import from URL'}
            </button>
          </form>
        )}

        {/* Standard ontologies */}
        {mode === 'standard' && (
          <div className="flex flex-col gap-3">
            {STANDARD_ONTOLOGIES.map((std) => (
              <label
                key={std.id}
                className="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all"
                style={{
                  borderColor: selectedStandard === std.id ? 'var(--color-primary)' : 'var(--color-border)',
                  backgroundColor: selectedStandard === std.id ? 'rgba(47,129,247,0.1)' : 'var(--color-bg-surface)',
                }}
              >
                <input
                  type="radio"
                  name="standard"
                  value={std.id}
                  checked={selectedStandard === std.id}
                  onChange={(e) => setSelectedStandard(e.target.value)}
                  className="w-4 h-4"
                />
                <div>
                  <p className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>{std.label}</p>
                  <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>{std.url}</p>
                </div>
              </label>
            ))}
            <button
              onClick={handleStandardImport}
              disabled={!selectedStandard || importMutation.isPending}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50 mt-2"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              {importMutation.isPending && <LoadingSpinner size="sm" />}
              {importMutation.isPending ? 'Importing...' : 'Import Selected'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
