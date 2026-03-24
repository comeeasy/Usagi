import { ZoomIn, ZoomOut, Maximize2, LayoutGrid } from 'lucide-react'

interface GraphControlsProps {
  onLayoutChange?: (layout: string) => void
  onZoomIn?: () => void
  onZoomOut?: () => void
  onFit?: () => void
  onFilterChange?: (filter: { concepts: boolean; individuals: boolean }) => void
  currentLayout?: string
}

const layouts = [
  { value: 'dagre', label: 'Dagre' },
  { value: 'circle', label: 'Circle' },
  { value: 'grid', label: 'Grid' },
  { value: 'concentric', label: 'Concentric' },
]

export default function GraphControls({
  onLayoutChange,
  onZoomIn,
  onZoomOut,
  onFit,
  onFilterChange,
  currentLayout = 'dagre',
}: GraphControlsProps) {
  const btnStyle = {
    backgroundColor: 'var(--color-bg-elevated)',
    border: '1px solid var(--color-border)',
    color: 'var(--color-text-secondary)',
  }

  return (
    <div
      className="flex items-center gap-2 p-2 rounded-lg border flex-wrap"
      style={{ backgroundColor: 'var(--color-bg-surface)', borderColor: 'var(--color-border)' }}
    >
      {/* Layout selector */}
      <div className="flex items-center gap-1">
        <LayoutGrid size={14} style={{ color: 'var(--color-text-muted)' }} />
        <select
          value={currentLayout}
          onChange={(e) => onLayoutChange?.(e.target.value)}
          className="text-xs px-2 py-1 rounded border"
          style={btnStyle}
        >
          {layouts.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      <div className="w-px h-5 self-center" style={{ backgroundColor: 'var(--color-border)' }} />

      {/* Zoom controls */}
      <div className="flex items-center gap-1">
        <button
          onClick={onZoomIn}
          className="p-1.5 rounded hover:opacity-80"
          style={btnStyle}
          title="Zoom In"
        >
          <ZoomIn size={14} />
        </button>
        <button
          onClick={onZoomOut}
          className="p-1.5 rounded hover:opacity-80"
          style={btnStyle}
          title="Zoom Out"
        >
          <ZoomOut size={14} />
        </button>
        <button
          onClick={onFit}
          className="p-1.5 rounded hover:opacity-80"
          style={btnStyle}
          title="Fit to screen"
        >
          <Maximize2 size={14} />
        </button>
      </div>

      <div className="w-px h-5 self-center" style={{ backgroundColor: 'var(--color-border)' }} />

      {/* Filter toggles */}
      <div className="flex items-center gap-2 text-xs">
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            defaultChecked
            onChange={(e) => onFilterChange?.({ concepts: e.target.checked, individuals: true })}
            className="w-3 h-3"
          />
          <span
            className="px-1.5 py-0.5 rounded"
            style={{ backgroundColor: 'rgba(47,129,247,0.2)', color: 'var(--color-primary)' }}
          >
            Concepts
          </span>
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            defaultChecked
            onChange={(e) => onFilterChange?.({ concepts: true, individuals: e.target.checked })}
            className="w-3 h-3"
          />
          <span
            className="px-1.5 py-0.5 rounded"
            style={{ backgroundColor: 'rgba(63,185,80,0.2)', color: 'var(--color-success)' }}
          >
            Individuals
          </span>
        </label>
      </div>
    </div>
  )
}
