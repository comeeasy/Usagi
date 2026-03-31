import { useState } from 'react'
import { Plus, X } from 'lucide-react'

const CHARACTERISTICS = [
  'Functional',
  'InverseFunctional',
  'Transitive',
  'Symmetric',
  'Asymmetric',
  'Reflexive',
  'Irreflexive',
]

const XSD_DATATYPES = [
  'xsd:string',
  'xsd:integer',
  'xsd:decimal',
  'xsd:float',
  'xsd:double',
  'xsd:boolean',
  'xsd:date',
  'xsd:dateTime',
  'xsd:anyURI',
  'xsd:langString',
]

interface PropertyFormProps {
  propertyType?: 'object' | 'data'
  initialValues?: {
    iri?: string
    label?: string
    comment?: string
    domain?: string[]
    range?: string[]
    characteristics?: string[]
    inverseOf?: string
    isFunctional?: boolean
  }
  onSubmit?: (values: unknown) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
  iriPrefix?: string
}

export default function PropertyForm({
  propertyType: initialType = 'object',
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
  iriPrefix,
}: PropertyFormProps) {
  const [propType, setPropType] = useState(initialType)
  const [iri, setIri] = useState(initialValues?.iri ?? (mode === 'create' ? (iriPrefix ?? '') : ''))
  const [label, setLabel] = useState(initialValues?.label ?? '')
  const [comment, setComment] = useState(initialValues?.comment ?? '')
  const [domain, setDomain] = useState<string[]>(initialValues?.domain ?? [])
  const [range, setRange] = useState<string[]>(initialValues?.range ?? [])
  const [characteristics, setCharacteristics] = useState<string[]>(initialValues?.characteristics ?? [])
  const [inverseOf, setInverseOf] = useState(initialValues?.inverseOf ?? '')
  const [isFunctional, setIsFunctional] = useState(initialValues?.isFunctional ?? false)
  const [newDomain, setNewDomain] = useState('')
  const [newRange, setNewRange] = useState('')
  const [newXsdRange, setNewXsdRange] = useState('xsd:string')

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const labelStyle = { color: 'var(--color-text-secondary)' }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit?.({ iri, label, comment, domain, range, characteristics, inverseOf, isFunctional, propertyType: propType })
  }

  const addDomain = () => {
    if (newDomain.trim() && !domain.includes(newDomain.trim())) {
      setDomain([...domain, newDomain.trim()])
      setNewDomain('')
    }
  }

  const addRange = () => {
    if (propType === 'object') {
      if (newRange.trim() && !range.includes(newRange.trim())) {
        setRange([...range, newRange.trim()])
        setNewRange('')
      }
    } else {
      if (!range.includes(newXsdRange)) {
        setRange([...range, newXsdRange])
      }
    }
  }

  const toggleCharacteristic = (c: string) => {
    setCharacteristics(
      characteristics.includes(c)
        ? characteristics.filter((x) => x !== c)
        : [...characteristics, c]
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Type tabs */}
      <div className="flex border rounded overflow-hidden" style={{ borderColor: 'var(--color-border)' }}>
        {(['object', 'data'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setPropType(t)}
            className="flex-1 py-1.5 text-sm capitalize transition-colors"
            style={{
              backgroundColor: propType === t ? 'var(--color-primary)' : 'var(--color-bg-elevated)',
              color: propType === t ? '#fff' : 'var(--color-text-secondary)',
            }}
          >
            {t} Property
          </button>
        ))}
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>IRI *</label>
        <input type="text" value={iri} onChange={(e) => setIri(e.target.value)} placeholder="https://example.org/myProperty"
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} required disabled={mode === 'edit'} />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Label</label>
        <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label"
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none" style={inputStyle} />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Comment</label>
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2}
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none resize-none" style={inputStyle} />
      </div>

      {/* Domain */}
      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Domain</label>
        <div className="flex flex-wrap gap-1 mb-1">
          {domain.map((d) => (
            <span key={d} className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-mono"
              style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-info)' }}>
              {d} <button type="button" onClick={() => setDomain(domain.filter((x) => x !== d))}><X size={10} /></button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          <input type="text" value={newDomain} onChange={(e) => setNewDomain(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addDomain())}
            placeholder="Domain IRI" className="flex-1 px-2 py-1 rounded border text-xs font-mono focus:outline-none" style={inputStyle} />
          <button type="button" onClick={addDomain} className="px-2 py-1 rounded border hover:opacity-80"
            style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
            <Plus size={12} />
          </button>
        </div>
      </div>

      {/* Range */}
      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>Range</label>
        <div className="flex flex-wrap gap-1 mb-1">
          {range.map((r) => (
            <span key={r} className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-mono"
              style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-info)' }}>
              {r} <button type="button" onClick={() => setRange(range.filter((x) => x !== r))}><X size={10} /></button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          {propType === 'object' ? (
            <input type="text" value={newRange} onChange={(e) => setNewRange(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRange())}
              placeholder="Range IRI" className="flex-1 px-2 py-1 rounded border text-xs font-mono focus:outline-none" style={inputStyle} />
          ) : (
            <select value={newXsdRange} onChange={(e) => setNewXsdRange(e.target.value)}
              className="flex-1 px-2 py-1 rounded border text-xs" style={inputStyle}>
              {XSD_DATATYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          <button type="button" onClick={addRange} className="px-2 py-1 rounded border hover:opacity-80"
            style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
            <Plus size={12} />
          </button>
        </div>
      </div>

      {/* Object property extras */}
      {propType === 'object' && (
        <>
          <div>
            <label className="block text-xs mb-2 font-medium" style={labelStyle}>Characteristics</label>
            <div className="flex flex-wrap gap-2">
              {CHARACTERISTICS.map((c) => (
                <label key={c} className="flex items-center gap-1 text-xs cursor-pointer">
                  <input type="checkbox" checked={characteristics.includes(c)} onChange={() => toggleCharacteristic(c)} className="w-3 h-3" />
                  <span style={{ color: 'var(--color-text-secondary)' }}>{c}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-xs mb-1 font-medium" style={labelStyle}>Inverse Of</label>
            <input type="text" value={inverseOf} onChange={(e) => setInverseOf(e.target.value)}
              placeholder="Inverse property IRI" className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono" style={inputStyle} />
          </div>
        </>
      )}

      {/* Data property: functional */}
      {propType === 'data' && (
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={isFunctional} onChange={(e) => setIsFunctional(e.target.checked)} />
          <span style={labelStyle}>Functional</span>
        </label>
      )}

      <div className="flex gap-2 pt-2">
        <button type="submit" className="px-4 py-1.5 rounded text-sm font-medium hover:opacity-80"
          style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}>
          {mode === 'create' ? 'Create' : 'Save'}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="px-4 py-1.5 rounded text-sm hover:opacity-80"
            style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)' }}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
