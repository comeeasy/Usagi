import { useRef, useEffect, useCallback, useState } from 'react'
import { EditorView, keymap, lineNumbers, highlightActiveLine } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { Save, X } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { getGraphTtl, putGraphTtl } from '@/api/ontologies'
import { useDataset } from '@/contexts/DatasetContext'
import LoadingSpinner from '@/components/shared/LoadingSpinner'

const darkTheme = EditorView.theme(
  {
    '&': {
      backgroundColor: 'var(--color-bg-elevated)',
      color: 'var(--color-text-primary)',
      fontSize: '13px',
      height: '100%',
    },
    '.cm-content': {
      caretColor: 'var(--color-primary)',
      padding: '8px',
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    },
    '.cm-line': { padding: '0 4px' },
    '.cm-activeLine': { backgroundColor: 'rgba(47,129,247,0.08)' },
    '.cm-gutters': {
      backgroundColor: 'var(--color-bg-surface)',
      borderRight: '1px solid var(--color-border)',
      color: 'var(--color-text-muted)',
    },
    '.cm-activeLineGutter': { backgroundColor: 'rgba(47,129,247,0.1)' },
    '&.cm-focused .cm-cursor': { borderLeftColor: 'var(--color-primary)' },
    '.cm-scroller': { overflow: 'auto' },
  },
  { dark: true },
)

interface TtlEditorPanelProps {
  ontologyId: string
  graphIri: string
  onClose: () => void
}

export default function TtlEditorPanel({ ontologyId, graphIri, onClose }: TtlEditorPanelProps) {
  const { dataset } = useDataset()
  const queryClient = useQueryClient()

  const [ttl, setTtl] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onChangeRef = useRef<(v: string) => void>(() => {})

  // Load TTL on mount
  useEffect(() => {
    getGraphTtl(ontologyId, graphIri, dataset)
      .then((text) => setTtl(text))
      .catch((e) => setLoadError(String(e)))
  }, [ontologyId, graphIri, dataset])

  // Init editor once TTL is loaded
  const initEditor = useCallback((initial: string) => {
    if (!containerRef.current) return
    viewRef.current?.destroy()

    const state = EditorState.create({
      doc: initial,
      extensions: [
        lineNumbers(),
        highlightActiveLine(),
        darkTheme,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            onChangeRef.current(update.state.doc.toString())
          }
        }),
        EditorView.lineWrapping,
        keymap.of([
          {
            key: 'Escape',
            run: () => { onClose(); return true },
          },
        ]),
      ],
    })
    viewRef.current = new EditorView({ state, parent: containerRef.current })
  }, [onClose])

  useEffect(() => {
    if (ttl !== null) initEditor(ttl)
    return () => { viewRef.current?.destroy(); viewRef.current = null }
  }, [ttl, initEditor])

  const saveMutation = useMutation({
    mutationFn: (turtle: string) => putGraphTtl(ontologyId, graphIri, turtle, dataset),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['named-graphs', ontologyId, dataset] })
      onClose()
    },
    onError: (e) => setSaveError(String(e)),
  })

  const handleSave = () => {
    const current = viewRef.current?.state.doc.toString() ?? ''
    setSaveError(null)
    saveMutation.mutate(current)
  }

  const shortIri = graphIri.split('/').pop() ?? graphIri

  return (
    <div
      className="flex flex-col rounded-lg border overflow-hidden"
      style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-elevated)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 flex-shrink-0 border-b"
        style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
      >
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-xs font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Edit TTL — {shortIri}
          </span>
          <span
            className="text-xs font-mono truncate max-w-xs"
            style={{ color: 'var(--color-text-muted)' }}
            title={graphIri}
          >
            {graphIri}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={handleSave}
            disabled={ttl === null || saveMutation.isPending}
            className="flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium hover:opacity-80 disabled:opacity-40"
            style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
          >
            {saveMutation.isPending ? <LoadingSpinner size="sm" /> : <Save size={12} />}
            Save
          </button>
          <button
            onClick={onClose}
            className="p-1 rounded hover:opacity-70"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Error banners */}
      {(loadError || saveError) && (
        <div
          className="px-3 py-2 text-xs"
          style={{ backgroundColor: '#ef444420', color: '#ef4444', borderBottom: '1px solid #ef444440' }}
        >
          {loadError ?? saveError}
        </div>
      )}

      {/* Editor area */}
      {ttl === null && !loadError ? (
        <div className="flex justify-center items-center py-10">
          <LoadingSpinner />
        </div>
      ) : (
        <div
          ref={containerRef}
          style={{ minHeight: 240, maxHeight: 480, overflowY: 'auto' }}
        />
      )}
    </div>
  )
}
