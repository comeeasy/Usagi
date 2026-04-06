import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Upload, Link, BookOpen, CheckCircle } from 'lucide-react'
import OntologyTabs from '@/components/layout/OntologyTabs'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { useMutation } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import {
  importOntologyFile,
  importOntologyUrl,
  importOntologyStandard,
  type ImportResult,
} from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'

type FileImportProgress = { phase: 'upload' | 'server'; uploadPct?: number }

function formatImportError(err: unknown): string {
  if (err instanceof ApiError) {
    const parts = [err.error, err.detail].filter(Boolean)
    return parts.length ? parts.join(': ') : err.message
  }
  if (err instanceof Error) return err.message
  return 'Unknown error'
}

type ImportMode = 'file' | 'url' | 'standard'

// backend keys: schema.org, foaf, dc, skos, owl, rdfs
const STANDARD_ONTOLOGIES = [
  { id: 'schema.org', label: 'Schema.org', description: 'https://schema.org/' },
  { id: 'foaf', label: 'FOAF', description: 'http://xmlns.com/foaf/spec/' },
  { id: 'dc', label: 'Dublin Core Terms', description: 'https://purl.org/dc/terms/' },
  { id: 'skos', label: 'SKOS', description: 'https://www.w3.org/2004/02/skos/' },
]

const FORMATS = ['turtle', 'rdf-xml', 'json-ld', 'n-triples', 'n-quads']

export default function ImportPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const { dataset } = useDataset()
  const [mode, setMode] = useState<ImportMode>('file')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('turtle')
  const [selectedStandard, setSelectedStandard] = useState<string | null>(null)
  const [fileImportProgress, setFileImportProgress] = useState<FileImportProgress | null>(null)

  const importMutation = useMutation({
    mutationFn: (fn: () => Promise<ImportResult>) => fn(),
    onSettled: () => setFileImportProgress(null),
  })

  const handleFileImport = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setFileImportProgress({ phase: 'upload', uploadPct: 0 })
    importMutation.mutate(() =>
      importOntologyFile(ontologyId!, file, dataset, (p) => {
        if (p.phase === 'upload') {
          const uploadPct =
            p.total > 0 ? Math.round((100 * p.loaded) / p.total) : undefined
          setFileImportProgress({ phase: 'upload', uploadPct })
        } else {
          setFileImportProgress({ phase: 'server' })
        }
      }),
    )
  }

  const handleUrlImport = (e: React.FormEvent) => {
    e.preventDefault()
    importMutation.mutate(() => importOntologyUrl(ontologyId!, url, dataset))
  }

  const handleStandardImport = () => {
    if (!selectedStandard) return
    importMutation.mutate(() => importOntologyStandard(ontologyId!, selectedStandard, dataset))
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
        {importMutation.isSuccess && importMutation.data && (
          <div
            role="status"
            aria-live="polite"
            className="p-4 rounded-lg border mb-4 text-sm"
            style={{
              borderColor: 'var(--color-success)',
              color: 'var(--color-text-primary)',
              backgroundColor: 'rgba(63,185,80,0.12)',
            }}
          >
            <div className="flex items-center gap-2 font-semibold mb-2" style={{ color: 'var(--color-success)' }}>
              <CheckCircle size={18} />
              Import finished successfully
            </div>
            <p className="mb-1">{importMutation.data.message}</p>
            {importMutation.data.timing_ms && (
              <p className="text-xs mt-2 font-mono" style={{ color: 'var(--color-text-muted)' }}>
                Server timing: read {importMutation.data.timing_ms.read} ms · parse{' '}
                {importMutation.data.timing_ms.parse} ms · store {importMutation.data.timing_ms.store} ms · total{' '}
                {importMutation.data.timing_ms.total} ms
              </p>
            )}
            {(importMutation.data.format || importMutation.data.graph_iri) && (
              <ul className="text-xs mt-2 space-y-0.5 font-mono" style={{ color: 'var(--color-text-muted)' }}>
                {importMutation.data.format != null && importMutation.data.format !== '' && (
                  <li>Detected format: {importMutation.data.format}</li>
                )}
                {importMutation.data.graph_iri != null && importMutation.data.graph_iri !== '' && (
                  <li className="break-all" title={importMutation.data.graph_iri}>
                    Target graph: {importMutation.data.graph_iri}
                  </li>
                )}
              </ul>
            )}
          </div>
        )}

        {/* Error */}
        {importMutation.isError && importMutation.error && (
          <div
            role="alert"
            className="p-4 rounded-lg border mb-4 text-sm"
            style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}
          >
            <p className="font-semibold mb-1">Import failed</p>
            <p className="break-words" style={{ color: 'var(--color-text-primary)' }}>
              {formatImportError(importMutation.error)}
            </p>
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
                  .ttl, .rdf, .owl, .xml, .jsonld, .nt, .n3, .trig, .nq
                </p>
              </div>
              <input
                id="file-input"
                type="file"
                className="hidden"
                accept=".ttl,.rdf,.owl,.xml,.jsonld,.json,.nt,.n3,.trig,.nq"
                onChange={(e) => {
                  importMutation.reset()
                  setFile(e.target.files?.[0] ?? null)
                }}
              />
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Large files may take a while. Keep this page open until you see the result below.
            </p>
            {importMutation.isPending && fileImportProgress && (
              <div
                role="status"
                aria-live="polite"
                className="p-3 rounded-lg border text-sm"
                style={{
                  borderColor: 'var(--color-border)',
                  backgroundColor: 'var(--color-bg-elevated)',
                  color: 'var(--color-text-primary)',
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <LoadingSpinner size="sm" />
                  <span>
                    {fileImportProgress.phase === 'upload'
                      ? 'Uploading file to server…'
                      : 'Server: parsing RDF and writing to Fuseki…'}
                  </span>
                </div>
                {fileImportProgress.phase === 'upload' && fileImportProgress.uploadPct != null && (
                  <progress
                    className="w-full h-2 rounded"
                    value={fileImportProgress.uploadPct}
                    max={100}
                  />
                )}
                {fileImportProgress.phase === 'upload' && fileImportProgress.uploadPct != null && (
                  <p className="text-xs mt-1 font-mono" style={{ color: 'var(--color-text-muted)' }}>
                    {fileImportProgress.uploadPct}%
                  </p>
                )}
              </div>
            )}
            <button
              type="submit"
              disabled={!file || importMutation.isPending}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded text-sm font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
            >
              {importMutation.isPending && <LoadingSpinner size="sm" />}
              {importMutation.isPending ? 'Importing…' : 'Import File'}
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
              <input type="url" value={url} onChange={(e) => { importMutation.reset(); setUrl(e.target.value) }} required
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
                  onChange={(e) => {
                    importMutation.reset()
                    setSelectedStandard(e.target.value)
                  }}
                  className="w-4 h-4"
                />
                <div>
                  <p className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>{std.label}</p>
                  <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>{std.description}</p>
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
