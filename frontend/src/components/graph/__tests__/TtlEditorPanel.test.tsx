/**
 * TtlEditorPanel.test.tsx — Section 31 F1~F4
 *
 * CodeMirror는 jsdom에서 DOM 렌더링이 불완전하므로 mock 처리.
 * API 함수는 vi.mock으로 교체.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../../../tests/utils'
import TtlEditorPanel from '../TtlEditorPanel'

// ── CodeMirror mock ────────────────────────────────────────────────────────────
vi.mock('@codemirror/view', () => {
  const EditorViewMock = vi.fn().mockImplementation(() => ({
    state: { doc: { toString: () => '@prefix owl: <http://www.w3.org/2002/07/owl#> .\n' } },
    destroy: vi.fn(),
  })) as unknown as Record<string, unknown>
  EditorViewMock.theme = vi.fn(() => ({}))
  EditorViewMock.updateListener = { of: vi.fn(() => ({})) }
  EditorViewMock.lineWrapping = {}
  return {
    EditorView: EditorViewMock,
    keymap: { of: vi.fn(() => ({})) },
    lineNumbers: vi.fn(() => ({})),
    highlightActiveLine: vi.fn(() => ({})),
  }
})
vi.mock('@codemirror/state', () => ({
  EditorState: {
    create: vi.fn().mockReturnValue({}),
  },
}))

// ── API mock ───────────────────────────────────────────────────────────────────
const mockGetGraphTtl = vi.fn()
const mockPutGraphTtl = vi.fn()

vi.mock('@/api/ontologies', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/ontologies')>()
  return {
    ...actual,
    getGraphTtl: (...args: unknown[]) => mockGetGraphTtl(...args),
    putGraphTtl: (...args: unknown[]) => mockPutGraphTtl(...args),
  }
})

const SAMPLE_TTL = '@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<https://ex.org/A> a owl:Class .\n'

const ONTOLOGY_ID = 'test-ont-uuid'
const GRAPH_IRI = 'https://test.example.org/ontology/manual'

function renderPanel(onClose = vi.fn()) {
  return renderWithProviders(
    <TtlEditorPanel
      ontologyId={ONTOLOGY_ID}
      graphIri={GRAPH_IRI}
      onClose={onClose}
    />,
  )
}

describe('TtlEditorPanel', () => {
  beforeEach(() => {
    mockGetGraphTtl.mockResolvedValue(SAMPLE_TTL)
    mockPutGraphTtl.mockResolvedValue(undefined)
  })

  // F1 — TTL 로드 후 에디터 표시
  it('F1: shows header with graph name after loading', async () => {
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/edit ttl — manual/i)).toBeInTheDocument()
    })
    expect(mockGetGraphTtl).toHaveBeenCalledWith(ONTOLOGY_ID, GRAPH_IRI, expect.anything())
  })

  it('F1: shows loading spinner before TTL is loaded', () => {
    mockGetGraphTtl.mockReturnValue(new Promise(() => {})) // never resolves
    renderPanel()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  // F2 — Save 버튼 → PUT 호출 후 onClose
  it('F2: Save button calls putGraphTtl and closes panel', async () => {
    const onClose = vi.fn()
    renderPanel(onClose)

    // Wait for TTL to load (Save button becomes enabled)
    const saveBtn = await screen.findByRole('button', { name: /save/i })
    expect(saveBtn).not.toBeDisabled()

    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(mockPutGraphTtl).toHaveBeenCalledWith(
        ONTOLOGY_ID,
        GRAPH_IRI,
        expect.any(String),
        expect.anything(),
      )
    })
    expect(onClose).toHaveBeenCalledOnce()
  })

  // F3 — Close(X) 버튼 → onClose 호출
  it('F3: Close button calls onClose', async () => {
    const onClose = vi.fn()
    renderPanel(onClose)
    await screen.findByRole('button', { name: /save/i })

    const closeBtn = screen.getByRole('button', { name: '' })
    // X 버튼은 aria-label 없이 icon만 있으므로 위치로 찾기
    const allButtons = screen.getAllByRole('button')
    const xButton = allButtons[allButtons.length - 1] // 마지막 버튼 = X
    fireEvent.click(xButton)

    expect(onClose).toHaveBeenCalledOnce()
  })

  // F4 — 로드 실패 시 에러 메시지
  it('F4: shows error message when TTL load fails', async () => {
    mockGetGraphTtl.mockRejectedValue(new Error('Failed to load TTL: 500'))
    renderPanel()

    await waitFor(() => {
      expect(screen.getByText(/failed to load ttl/i)).toBeInTheDocument()
    })
  })
})
