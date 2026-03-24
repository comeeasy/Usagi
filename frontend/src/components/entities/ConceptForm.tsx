import { useState } from 'react'
import { Plus, X } from 'lucide-react'

interface ConceptFormValues {
  iri: string
  label: string
  comment: string
  parentIris: string[]
}

interface ConceptFormProps {
  initialValues?: {
    iri?: string
    label?: string
    comment?: string
    parentIris?: string[]
  }
  onSubmit?: (values: ConceptFormValues) => void
  onCancel?: () => void
  mode?: 'create' | 'edit'
}

export default function ConceptForm({
  initialValues,
  onSubmit,
  onCancel,
  mode = 'create',
}: ConceptFormProps) {
  const [iri, setIri] = useState(initialValues?.iri ?? '')
  const [label, setLabel] = useState(initialValues?.label ?? '')
  const [comment, setComment] = useState(initialValues?.comment ?? '')
  const [parentIris, setParentIris] = useState<string[]>(initialValues?.parentIris ?? [])
  const [newParent, setNewParent] = useState('')

  const addParent = () => {
    if (newParent.trim() && !parentIris.includes(newParent.trim())) {
      setParentIris([...parentIris, newParent.trim()])
      setNewParent('')
    }
  }

  const removeParent = (p: string) => {
    setParentIris(parentIris.filter((x) => x !== p))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit?.({ iri, label, comment, parentIris })
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
          rows={3}
          className="w-full px-3 py-1.5 rounded border text-sm focus:outline-none resize-none"
          style={inputStyle}
        />
      </div>

      <div>
        <label className="block text-xs mb-1 font-medium" style={labelStyle}>
          Parent Classes
        </label>
        <div className="flex gap-1 flex-wrap mb-2">
          {parentIris.map((p) => (
            <span
              key={p}
              className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-mono"
              style={{
                backgroundColor: 'var(--color-bg-elevated)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-info)',
              }}
            >
              {p}
              <button type="button" onClick={() => removeParent(p)} className="hover:opacity-80">
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          <input
            type="text"
            value={newParent}
            onChange={(e) => setNewParent(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addParent())}
            placeholder="https://example.org/ParentClass"
            className="flex-1 px-3 py-1.5 rounded border text-sm focus:outline-none font-mono"
            style={inputStyle}
          />
          <button
            type="button"
            onClick={addParent}
            className="px-2 py-1.5 rounded border text-sm flex items-center gap-1 hover:opacity-80"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)',
            }}
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

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
