/**
 * NamedGraphsContext — 온톨로지별 선택된 Named Graph IRI 목록 전역 관리
 *
 * - 처음 로드 시 해당 온톨로지의 모든 Named Graph를 자동 선택
 * - 체크박스로 개별/전체 선택/해제 지원
 * - selectedGraphIris가 빈 배열이면 → 백엔드에 graph_iris 파라미터 미전송 (전체 조회)
 *   실제로는 "로드된 그래프 전체" 를 명시적으로 전달한다.
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface NamedGraphsContextValue {
  /** 현재 선택된 graph IRI 목록. 빈 배열 = 전체 (no filter). */
  selectedGraphIris: string[]
  /** 모든 알려진 graph IRI 목록 (listNamedGraphs 결과 기반). */
  allGraphIris: string[]
  /** allGraphIris를 업데이트하고, 처음 로드 시 전체 선택. */
  setKnownGraphs: (iris: string[]) => void
  /** 개별 graph IRI 토글. */
  toggleGraph: (iri: string) => void
  /** 전체 선택. */
  selectAll: () => void
  /** 전체 해제. */
  deselectAll: () => void
}

const NamedGraphsContext = createContext<NamedGraphsContextValue | null>(null)

export function NamedGraphsProvider({ children }: { children: ReactNode }) {
  const [allGraphIris, setAllGraphIris] = useState<string[]>([])
  const [selectedGraphIris, setSelectedGraphIris] = useState<string[]>([])
  const [initialized, setInitialized] = useState(false)

  const setKnownGraphs = useCallback((iris: string[]) => {
    setAllGraphIris(iris)
    if (!initialized && iris.length > 0) {
      // 처음 로드 시 전체 선택
      setSelectedGraphIris(iris)
      setInitialized(true)
    } else if (initialized) {
      // 새로 추가된 graph IRI는 자동 선택
      setSelectedGraphIris((prev) => {
        const prevSet = new Set(prev)
        const added = iris.filter((iri) => !prevSet.has(iri))
        return added.length > 0 ? [...prev, ...added] : prev
      })
    }
  }, [initialized])

  const toggleGraph = useCallback((iri: string) => {
    setSelectedGraphIris((prev) =>
      prev.includes(iri) ? prev.filter((i) => i !== iri) : [...prev, iri],
    )
  }, [])

  const selectAll = useCallback(() => {
    setSelectedGraphIris([...allGraphIris])
  }, [allGraphIris])

  const deselectAll = useCallback(() => {
    setSelectedGraphIris([])
  }, [])

  return (
    <NamedGraphsContext.Provider
      value={{ selectedGraphIris, allGraphIris, setKnownGraphs, toggleGraph, selectAll, deselectAll }}
    >
      {children}
    </NamedGraphsContext.Provider>
  )
}

export function useNamedGraphs(): NamedGraphsContextValue {
  const ctx = useContext(NamedGraphsContext)
  if (!ctx) throw new Error('useNamedGraphs must be used inside NamedGraphsProvider')
  return ctx
}
