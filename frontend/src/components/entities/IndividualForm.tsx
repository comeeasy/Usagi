import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import IRIListSearchInput from '@/components/shared/IRIListSearchInput'
import IRISearchInput from '@/components/shared/IRISearchInput'

interface DataProp {
  property_iri: string
  value: string
  datatype?: string
}

interface ObjectProp {
  property_iri: string
  target_iri: string
}

interface IndividualFormValues {
  iri: string
  label: string
  typeIris: string[]
  dataProperties: DataProp[]
  objectProperties: ObjectProp[]
}

interface IndividualFormProps {
  initialValues?: {
    iri?: string
    label?: string
    typeIris?: string[]
    dataProperties?: DataProp[]
    objectProperties?: ObjectProp[]
  }
  onSubmit?: (values: IndividualFormValues) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
  iriPrefix?: string
}

export default function IndividualForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
  iriPrefix,
}: IndividualFormProps) {
  const [iri, setIri] = useState(initialValues?.iri ?? (mode === 'create' ? (iriPrefix ?? '') : ''))
  const [label, setLabel] = useState(initialValues?.label ?? '')
  const [typeIris, setTypeIris] = useState<string[]>(initialValues?.typeIris ?? [])
  const [dataProperties, setDataProperties] = useState<DataProp[]>(initialValues?.dataProperties ?? [])
  const [objectProperties, setObjectProperties] = useState<ObjectProp[]>(initialValues?.objectProperties ?? [])

  const inputStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    borderColor: 'var(--color-border)',
    color: 'var(--color-text-primary)',
  }

  const labelStyle = { color: 'var(--color-text-secondary)' }

  const addDataProp = () => {
    setDataProperties([...dataProperties, { property_iri: '', value: '' }])
  }

  const updateDataProp = (i: number, field: keyof DataProp, value: string) => {
    const updated = [...dataProperties]
    updated[i] = { ...updated[i], [field]: value }
    setDataProperties(updated)
  }

  const addObjectProp = () => {
    setObjectProperties([...objectProperties, { property_iri: '', target_iri: '' }])
  }

  const updateObjectProp = (i: number, field: keyof ObjectProp, value: string) => {
    const updated = [...objectProperties]
    updated[i] = { ...updated[i], [field]: value }
    setObjectProperties(updated)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit?.({ iri, label, typeIris, dataProperties, objectProperties })
  }

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
          placeholder="https://example.org/myIndividual"
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
          placeholder="Label"
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none"
          style={inputStyle}
        />
      </div>

      <IRIListSearchInput
        label="Types"
        values={typeIris}
        onChange={setTypeIris}
        placeholder="Search or enter class IRI…"
        kind="concept"
      />

      {/* Data Properties */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium" style={labelStyle}>Data Properties</label>
          <button type="button" onClick={addDataProp} className="text-xs flex items-center gap-1 hover:opacity-80"
            style={{ color: 'var(--color-primary)' }}>
            <Plus size={12} /> Add
          </button>
        </div>
        {dataProperties.map((dp, i) => (
          <div key={i} className="flex gap-1 mb-1 items-center">
            <IRISearchInput
              value={dp.property_iri}
              onChange={(iri) => updateDataProp(i, 'property_iri', iri)}
              placeholder="Property IRI…"
              kind="property"
              className="flex-1"
            />
            <input
              type="text"
              value={dp.value}
              onChange={(e) => updateDataProp(i, 'value', e.target.value)}
              placeholder="Value"
              className="flex-1 px-2 py-1 rounded border text-xs focus:outline-none"
              style={inputStyle}
            />
            <button type="button" onClick={() => setDataProperties(dataProperties.filter((_, j) => j !== i))}
              className="px-1 hover:opacity-80" style={{ color: 'var(--color-error)' }}>
              <X size={12} />
            </button>
          </div>
        ))}
      </div>

      {/* Object Properties */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium" style={labelStyle}>Object Properties</label>
          <button type="button" onClick={addObjectProp} className="text-xs flex items-center gap-1 hover:opacity-80"
            style={{ color: 'var(--color-primary)' }}>
            <Plus size={12} /> Add
          </button>
        </div>
        {objectProperties.map((op, i) => (
          <div key={i} className="flex gap-1 mb-1 items-center">
            <IRISearchInput
              value={op.property_iri}
              onChange={(iri) => updateObjectProp(i, 'property_iri', iri)}
              placeholder="Property IRI…"
              kind="property"
              className="flex-1"
            />
            <IRISearchInput
              value={op.target_iri}
              onChange={(iri) => updateObjectProp(i, 'target_iri', iri)}
              placeholder="Target IRI…"
              kind="individual"
              className="flex-1"
            />
            <button type="button" onClick={() => setObjectProperties(objectProperties.filter((_, j) => j !== i))}
              className="px-1 hover:opacity-80" style={{ color: 'var(--color-error)' }}>
              <X size={12} />
            </button>
          </div>
        ))}
      </div>

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
