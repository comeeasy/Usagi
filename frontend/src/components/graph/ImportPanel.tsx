import { useState } from 'react'
import { Upload, Link, BookOpen, CheckCircle, X } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'
import {
  importOntologyFile,
  importOntologyUrl,
  importOntologyStandard,
  type ImportResult,
} from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import LoadingSpinner from '@/components/shared/LoadingSpinner'

type FileImportProgress = { phase: 'upload' | 'server'; uploadPct?: number }
type ImportMode = 'file' | 'url' | 'standard'

const STANDARD_ONTOLOGIES = [
  { id: 'schema.org', label: 'Schema.org', description: 'https://schema.org/' },
  { id: 'foaf', label: 'FOAF', description: 'http://xmlns.com/foaf/spec/' },
  { id: 'dc', label: 'Dublin Core Terms', description: 'https://purl.org/dc/terms/' },
  { id: 'skos', label: 'SKOS', description: 'https://www.w3.org/2004/02/skos/' },
]

const FORMATS = ['turtle', 'rdf-xml', 'json-ld', 'n-triples', 'n-quads']

function formatImportError(err: unknown): string {
  if (err instanceof ApiError) {
    const parts = [err.error, err.detail].filter(Boolean)
    return parts.length ? parts.join(': ') : err.message
  }
  if (err instanceof Error) return err.message
  return 'Unknown error'
}

interface ImportPanelProps {
  ontologyId: string
  onClose?: () => void
}

export default function ImportPanel({ ontologyId, onClose }: ImportPanelProps) {
  const { dataset } = useDataset()
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<ImportMode>('file')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState('turtle')
  const [selectedStandard, setSelectedStandard] = useState<string | null>(null)
  const [fileImportProgress, setFileImportProgress] = useState<FileImportProgress | null>(null)

  const importMutation = useMutation({
    mutationFn: (fn: () => Promise<ImportResult>) => fn(),
    onSettled: () => setFileImportProgress(null),
    onSuccess: () => {
      // Invalidate named graphs list so it refreshes
      queryClient.invalidateQueries({ queryKey: ['named-graphs', ontologyId] })
    },
  })

  const handleFileImport = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setFileImportProgress({ phase: 'upload', uploadPct: 0 })
    importMutation.mutate(() =>
      importOntologyFile(ontologyId, file, dataset, (p) => {
        if (p.phase === 'upload') {
          const uploadPct = p.total > 0 ? Math.round((100 * p.loaded) / p.total) : undefined
          setFileImportProgress({ phase: 'upload', uploadPct })
        } else {
          setFileImportProgress({ phase: 'server' })
        }
      }),
    )
  }

  const handleUrlImport = (e: React.FormEvent) => {
    e.preventDefault()
    importMutation.mutate(() => importOntologyUrl(ontologyId, url, dataset))
  }

  const handleStandardImport = () => {
    if (!selectedStandard) return
    importMutation.mutate(() => importOntologyStandard(ontologyId, selectedStandard, dataset))
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ borderLeft: '1px solid var(--color-border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3"
           style={{ borderBottom: '1px solid var(--color-border)' }}>
        <h3 className="text-sm font-semibold">Import Ontology</h3>
        {onClose && (
          <button onClick={onClose} className="p-1 rounded hover:opacity-60">
            <X size={16} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {/* Mode tabs */}
        <div className="flex gap-2 mb-4">
          {([
            { id: 'file', label: 'File', icon: Upload },
            { id: 'url', label: 'URL', icon: Link },
            { id: 'standard', label: 'Standard', icon: BookOpen },
          ] as const).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded border text-xs transition-all"
              style={{
                backgroundColor: mode === id ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
                borderColor: mode === id ? 'var(--color-primary)' : 'var(--color-border)',
                color: mode === id ? '#fff' : 'var(--color-text-secondary)',
              }}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>

        {/* Success */}
        {importMutation.isSuccess && importMutation.data && (
          <div className="p-3 rounded-lg border mb-4 text-xs"
               style={{ borderColor: 'var(--color-success)', backgroundColor: 'rgba(63,185,80,0.12)' }}>
            <div className="flex items-center gap-1.5 font-semibold mb-1"
                 style={{ color: 'var(--color-success)' }}>
              <CheckCircle size={14} />
              Import finished
            </div>
            <p>{importMutation.data.message}</p>
          </div>
        )}

        {/* Error */}
        {importMutation.isError && (
          <div className="p-3 rounded-lg border mb-4 text-xs"
               style={{ borderColor: 'var(--color-error)', color: 'var(--color-error)', backgroundColor: 'rgba(248,81,73,0.1)' }}>
            <p className="font-semibold mb-1">Import failed</p>
            <p style={{ color: 'var(--color-text-primary)' }}>{formatImportError(importMutation.error)}</p>
          </div>
        )}

        {/* File */}
        {mode === 'file' && (
          <form onSubmit={handleFileImport} className="flex flex-col gap-3">
            <select value={format} onChange={(e) => setFormat(e.target.value)}
              className="px-2 py-1 rounded border text-xs" style={inputStyle}>
              {FORMATS.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
            <div
              className="border-2 border-dashed rounded-lg p-6 flex flex-col items-center gap-2 cursor-pointer text-center"
              style={{ borderColor: file ? 'var(--color-success)' : 'var(--color-border)' }}
              onClick={() => document.getElementById('import-file-input')?.click()}
            >
              <Upload size={24} style={{ color: 'var(--color-text-muted)' }} />
              <p className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>
                {file ? file.name : 'Click to select file'}
              </p>
              <input id="import-file-input" type="file" className="hidden"
                accept=".ttl,.rdf,.owl,.xml,.jsonld,.json,.nt,.n3,.trig,.nq"
                onChange={(e) => { importMutation.reset(); setFile(e.target.files?.[0] ?? null) }} />
            </div>
            {importMutation.isPending && fileImportProgress && (
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {fileImportProgress.phase === 'upload' ? `Uploading… ${fileImportProgress.uploadPct ?? 0}%` : 'Writing to Fuseki…'}
              </p>
            )}
            <button type="submit" disabled={!file || importMutation.isPending}
              className="px-3 py-1.5 rounded text-xs font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
              {importMutation.isPending ? 'Importing…' : 'Import File'}
            </button>
          </form>
        )}

        {/* URL */}
        {mode === 'url' && (
          <form onSubmit={handleUrlImport} className="flex flex-col gap-3">
            <input type="url" value={url}
              onChange={(e) => { importMutation.reset(); setUrl(e.target.value) }}
              required placeholder="https://example.org/ontology.ttl"
              className="w-full px-2 py-1.5 rounded border text-xs focus:outline-none font-mono" style={inputStyle} />
            <button type="submit" disabled={!url || importMutation.isPending}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium hover:opacity-80 disabled:opacity-50"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
              {importMutation.isPending && <LoadingSpinner size="sm" />}
              {importMutation.isPending ? 'Importing…' : 'Import from URL'}
            </button>
          </form>
        )}

        {/* Standard */}
        {mode === 'standard' && (
          <div className="flex flex-col gap-2">
            {STANDARD_ONTOLOGIES.map((std) => (
              <label key={std.id}
                className="flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer"
                style={{
                  borderColor: selectedStandard === std.id ? 'var(--color-primary)' : 'var(--color-border)',
                  backgroundColor: selectedStandard === std.id ? 'rgba(47,129,247,0.1)' : 'var(--color-bg-surface)',
                }}>
                <input type="radio" name="standard" value={std.id}
                  checked={selectedStandard === std.id}
                  onChange={(e) => { importMutation.reset(); setSelectedStandard(e.target.value) }}
                  className="w-3 h-3" />
                <div>
                  <p className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>{std.label}</p>
                  <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>{std.description}</p>
                </div>
              </label>
            ))}
            <button onClick={handleStandardImport} disabled={!selectedStandard || importMutation.isPending}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium hover:opacity-80 disabled:opacity-50 mt-1"
              style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
              {importMutation.isPending && <LoadingSpinner size="sm" />}
              {importMutation.isPending ? 'Importing…' : 'Import Selected'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
