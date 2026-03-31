import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import type { PropertyRestriction, RestrictionType } from '@/types/concept'
import IRIListSearchInput from '@/components/shared/IRIListSearchInput'
import IRISearchInput from '@/components/shared/IRISearchInput'

const RESTRICTION_TYPES: { value: RestrictionType; label: string }[] = [
  { value: 'someValuesFrom', label: 'some (∃)' },
  { value: 'allValuesFrom', label: 'only (∀)' },
  { value: 'hasValue', label: 'value (=)' },
  { value: 'minCardinality', label: 'min' },
  { value: 'maxCardinality', label: 'max' },
  { value: 'exactCardinality', label: 'exactly' },
]

const CARDINALITY_TYPES: RestrictionType[] = ['minCardinality', 'maxCardinality', 'exactCardinality']

interface ConceptFormValues {
  iri: string
  label: string
  comment: string
  superClasses: string[]
  equivalentClasses: string[]
  disjointWith: string[]
  restrictions: PropertyRestriction[]
}

interface ConceptFormProps {
  initialValues?: {
    iri?: string
    label?: string
    comment?: string
    superClasses?: string[]
    equivalentClasses?: string[]
    disjointWith?: string[]
    restrictions?: PropertyRestriction[]
  }
  onSubmit?: (values: ConceptFormValues) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
  iriPrefix?: string
}


function RestrictionEditor({
  restrictions,
  onChange,
}: {
  restrictions: PropertyRestriction[]
  onChange: (r: PropertyRestriction[]) => void
}) {
  const [propIri, setPropIri] = useState('')
  const [rtype, setRtype] = useState<RestrictionType>('someValuesFrom')
  const [value, setValue] = useState('')
  const [cardinality, setCardinality] = useState('1')

  const addRestriction = () => {
    if (!propIri.trim()) return
    const r: PropertyRestriction = {
      property_iri: propIri.trim(),
      type: rtype,
      value: value.trim(),
      ...(CARDINALITY_TYPES.includes(rtype) ? { cardinality: parseInt(cardinality) || 1 } : {}),
    }
    onChange([...restrictions, r])
    setPropIri('')
    setValue('')
  }

  const needsCardinality = CARDINALITY_TYPES.includes(rtype)

  return (
    <div>
      <label className="block text-xs mb-1 font-medium" style={{ color: 'var(--color-text-secondary)' }}>
        Restrictions
      </label>

      {/* Existing */}
      {restrictions.length > 0 && (
        <div className="flex flex-col gap-1 mb-2">
          {restrictions.map((r, i) => (
            <div
              key={i}
              className="flex items-center justify-between text-xs p-2 rounded"
              style={{ backgroundColor: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)' }}
            >
              <span style={{ color: 'var(--color-text-secondary)' }}>
                <span style={{ color: 'var(--color-text-muted)' }}>{r.type}</span>
                {' '}<span className="font-mono" style={{ color: 'var(--color-info)' }}>{r.property_iri.split('#').pop() ?? r.property_iri}</span>
                {r.value && <> → <span className="font-mono">{r.value.split('#').pop() ?? r.value}</span></>}
                {r.cardinality !== undefined && <span> ({r.cardinality})</span>}
              </span>
              <button
                type="button"
                onClick={() => onChange(restrictions.filter((_, j) => j !== i))}
                className="hover:opacity-80 ml-2"
                style={{ color: 'var(--color-text-muted)' }}
              >
                <X size={10} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add new */}
      <div
        className="p-3 rounded border"
        style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
      >
        <p className="text-xs mb-2" style={{ color: 'var(--color-text-muted)' }}>Add restriction</p>
        <div className="flex gap-1 mb-1.5">
          <select
            value={rtype}
            onChange={(e) => setRtype(e.target.value as RestrictionType)}
            className="px-2 py-1.5 rounded border text-xs"
            style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
          >
            {RESTRICTION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          {needsCardinality && (
            <input
              type="number"
              value={cardinality}
              onChange={(e) => setCardinality(e.target.value)}
              min={0}
              className="w-16 px-2 py-1.5 rounded border text-xs"
              style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)', color: 'var(--color-text-primary)' }}
            />
          )}
        </div>
        <div className="mb-1.5">
          <IRISearchInput
            value={propIri}
            onChange={(iri) => setPropIri(iri)}
            placeholder="Search or enter property IRI…"
            kind="property"
          />
        </div>
        <div className="flex gap-1">
          <IRISearchInput
            value={value}
            onChange={(iri) => setValue(iri)}
            placeholder="Filler IRI or value…"
            kind="concept"
            className="flex-1"
          />
          <button
            type="button"
            onClick={addRestriction}
            disabled={!propIri.trim()}
            className="px-2 py-1.5 rounded border text-xs hover:opacity-80 disabled:opacity-40"
            style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
          >
            <Plus size={13} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ConceptForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
  iriPrefix,
}: ConceptFormProps) {
  const [iri, setIri] = useState(initialValues?.iri ?? (mode === 'create' ? (iriPrefix ?? '') : ''))
  const [label, setLabel] = useState(initialValues?.label ?? '')
  const [comment, setComment] = useState(initialValues?.comment ?? '')
  const [superClasses, setSuperClasses] = useState<string[]>(initialValues?.superClasses ?? [])
  const [equivalentClasses, setEquivalentClasses] = useState<string[]>(initialValues?.equivalentClasses ?? [])
  const [disjointWith, setDisjointWith] = useState<string[]>(initialValues?.disjointWith ?? [])
  const [restrictions, setRestrictions] = useState<PropertyRestriction[]>(initialValues?.restrictions ?? [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit?.({ iri, label, comment, superClasses, equivalentClasses, disjointWith, restrictions })
  }

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const labelStyle = { color: 'var(--color-text-secondary)' }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>
          IRI {mode === 'create' && <span style={{ color: 'var(--color-error)' }}>*</span>}
        </label>
        <input
          type="text"
          value={iri}
          onChange={(e) => setIri(e.target.value)}
          placeholder="https://example.org/MyClass"
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none font-mono"
          style={inputStyle}
          required={mode === 'create'}
          disabled={mode === 'edit'}
        />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>
          Label
        </label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Human readable label"
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none"
          style={inputStyle}
        />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>
          Comment
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Description of this class"
          rows={2}
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none resize-none"
          style={inputStyle}
        />
      </div>

      <IRIListSearchInput
        label="Parent Classes (rdfs:subClassOf)"
        values={superClasses}
        onChange={setSuperClasses}
        placeholder="Search or enter class IRI…"
        kind="concept"
      />

      <IRIListSearchInput
        label="Equivalent Classes (owl:equivalentClass)"
        values={equivalentClasses}
        onChange={setEquivalentClasses}
        placeholder="Search or enter class IRI…"
        kind="concept"
      />

      <IRIListSearchInput
        label="Disjoint With (owl:disjointWith)"
        values={disjointWith}
        onChange={setDisjointWith}
        placeholder="Search or enter class IRI…"
        kind="concept"
      />

      <RestrictionEditor restrictions={restrictions} onChange={setRestrictions} />

      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          className="px-4 py-1.5 rounded text-sm font-medium hover:opacity-80 transition-opacity"
          style={{ backgroundColor: 'var(--color-primary)', color: '#fff' }}
        >
          {mode === 'create' ? 'Create' : 'Save'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-1.5 rounded text-sm hover:opacity-80 transition-opacity"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)',
            }}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
