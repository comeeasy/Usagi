// TODO: 관계(Property) 검색 바
// 키워드, domain IRI 필터, range IRI 필터
// ObjectProperty / DataProperty 타입 탭

interface RelationSearchBarProps {
  onSearch?: (query: string, domainIri?: string, rangeIri?: string) => void
}

export default function RelationSearchBar({ onSearch }: RelationSearchBarProps) {
  return (
    <div className="flex gap-2 items-center">
      {/* TODO: search input, domain/range IRI filters */}
    </div>
  )
}
