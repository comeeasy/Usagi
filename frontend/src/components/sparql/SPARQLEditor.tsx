import { useRef, useEffect, useCallback } from 'react'
import { EditorView, keymap, lineNumbers, highlightActiveLine } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { Play } from 'lucide-react'

// Lazy-load SPARQL language
let sparqlLang: (() => import('@codemirror/state').Extension) | null = null
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require('@codemirror/lang-sparql')
  sparqlLang = mod.sparql ?? null
} catch {
  sparqlLang = null
}

interface SPARQLEditorProps {
  value?: string
  onChange?: (value: string) => void
  onExecute?: (query: string) => void
}

const darkTheme = EditorView.theme(
  {
    '&': {
      backgroundColor: 'var(--color-bg-elevated)',
      color: 'var(--color-text-primary)',
      fontSize: '13px',
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
  },
  { dark: true },
)

export default function SPARQLEditor({ value = '', onChange, onExecute }: SPARQLEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onExecuteRef = useRef(onExecute)
  const onChangeRef = useRef(onChange)

  useEffect(() => { onExecuteRef.current = onExecute }, [onExecute])
  useEffect(() => { onChangeRef.current = onChange }, [onChange])

  const initEditor = useCallback(() => {
    if (!containerRef.current) return
    if (viewRef.current) viewRef.current.destroy()

    const executeKeymap = keymap.of([
      {
        key: 'Ctrl-Enter',
        mac: 'Cmd-Enter',
        run: (view) => {
          onExecuteRef.current?.(view.state.doc.toString())
          return true
        },
      },
    ])

    const extensions: import('@codemirror/state').Extension[] = [
      lineNumbers(),
      highlightActiveLine(),
      executeKeymap,
      darkTheme,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChangeRef.current?.(update.state.doc.toString())
        }
      }),
      EditorView.lineWrapping,
    ]

    if (sparqlLang) extensions.push(sparqlLang())

    const state = EditorState.create({ doc: value, extensions })
    viewRef.current = new EditorView({ state, parent: containerRef.current })
  }, [])

  useEffect(() => {
    initEditor()
    return () => { viewRef.current?.destroy(); viewRef.current = null }
  }, [initEditor])

  // Sync external value changes
  useEffect(() => {
    if (!viewRef.current) return
    const current = viewRef.current.state.doc.toString()
    if (current !== value) {
      viewRef.current.dispatch({
        changes: { from: 0, to: current.length, insert: value },
      })
    }
  }, [value])

  return (
    <div
      className="flex flex-col rounded-lg border overflow-hidden"
      style={{ borderColor: 'var(--color-border)' }}
    >
      {/* Toolbar */}
      <div
        className="flex items-center justify-between px-3 py-1.5 border-b flex-shrink-0"
        style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
      >
        <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>SPARQL Query Editor</span>
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Ctrl+Enter to run</span>
          <button
            onClick={() => {
              const q = viewRef.current?.state.doc.toString() ?? value
              onExecute?.(q)
            }}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium hover:opacity-80 transition-opacity"
            style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
          >
            <Play size={11} />
            Run
          </button>
        </div>
      </div>

      {/* Editor mount */}
      <div ref={containerRef} style={{ minHeight: 200, maxHeight: 400, overflowY: 'auto' }} />
    </div>
  )
}
