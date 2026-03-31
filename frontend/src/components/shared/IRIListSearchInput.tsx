/**
 * IRIListSearchInput — IRI 목록 관리용 (태그 + 검색 드롭다운)
 *
 * - 선택한 IRI들을 chip으로 표시
 * - IRISearchInput으로 검색/추가
 */
import { X } from 'lucide-react'
import IRISearchInput, { type IRIKind } from './IRISearchInput'

interface IRIListSearchInputProps {
  label: string
  values: string[]
  onChange: (vals: string[]) => void
  placeholder?: string
  kind?: IRIKind
}

export default function IRIListSearchInput({
  label,
  values,
  onChange,
  placeholder,
  kind = 'concept',
}: IRIListSearchInputProps) {
  const add = (iri: string) => {
    const v = iri.trim()
    if (v && !values.includes(v)) onChange([...values, v])
  }

  return (
    <div>
      <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
        {label}
      </label>

      {/* 선택된 IRIs */}
      {values.length > 0 && (
        <div className="flex gap-1 flex-wrap mb-1.5">
          {values.map((v) => (
            <span
              key={v}
              className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-mono"
              style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-info)' }}
            >
              <span className="max-w-xs truncate">{v}</span>
              <button
                type="button"
                onClick={() => onChange(values.filter((x) => x !== v))}
                className="hover:opacity-80 flex-shrink-0"
              >
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* 검색 입력 */}
      <IRISearchInput
        value=""
        onChange={(iri) => { add(iri) }}
        placeholder={placeholder ?? `Search ${kind}s or enter IRI…`}
        kind={kind}
      />
    </div>
  )
}
