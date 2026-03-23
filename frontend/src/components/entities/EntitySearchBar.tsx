// TODO: 키워드 + 타입 필터 + 벡터 검색 토글
// debounce 적용 (300ms), 타입 선택: all | concept | individual
// 벡터 검색 토글 스위치

interface EntitySearchBarProps {
  onSearch?: (query: string, kind: string, vectorSearch: boolean) => void
}

export default function EntitySearchBar({ onSearch }: EntitySearchBarProps) {
  return (
    <div className="flex gap-2 items-center">
      {/* TODO: search input, kind selector, vector search toggle */}
    </div>
  )
}
