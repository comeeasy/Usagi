// TODO: CodeMirror + SPARQL 언어팩
// @codemirror/view, @codemirror/state, @codemirror/lang-sparql 사용
// 실행 버튼, 키보드 단축키 (Ctrl+Enter / Cmd+Enter)
// 다크 테마 적용

interface SPARQLEditorProps {
  value?: string
  onChange?: (value: string) => void
  onExecute?: (query: string) => void
}

export default function SPARQLEditor({ value = '', onChange, onExecute }: SPARQLEditorProps) {
  // TODO: useRef for CodeMirror EditorView
  // TODO: initialize CodeMirror with sparql() language extension
  // TODO: add keymap for Ctrl+Enter → onExecute

  return (
    <div className="border border-border rounded font-mono text-sm">
      {/* TODO: CodeMirror editor mount point */}
    </div>
  )
}
