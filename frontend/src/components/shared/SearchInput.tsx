// TODO: 공통 검색 입력 컴포넌트
// 돋보기 아이콘 (lucide-react), 클리어 버튼
// onChange debounce 지원

interface SearchInputProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
  debounceMs?: number
}

export default function SearchInput({
  value = '',
  onChange,
  placeholder = 'Search...',
  debounceMs = 300,
}: SearchInputProps) {
  return (
    <div className="relative flex items-center">
      {/* TODO: search icon + input + clear button */}
      <input
        type="text"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-8 pr-4 py-1.5 bg-bg-elevated border border-border rounded text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary"
      />
    </div>
  )
}
