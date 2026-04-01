export default function GraphLegend() {
  const items = [
    { color: '#2F81F7', label: 'Concept', shape: 'rect' },
    { color: '#3FB950', label: 'Individual', shape: 'circle' },
    { color: '#A371F7', label: 'Object Property', shape: 'line' },
    { color: '#30363D', label: 'Subclass / Type', shape: 'dashed' },
  ]

  return (
    <div
      className="flex flex-col gap-1.5 p-3 rounded-lg border text-xs"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      <p className="font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>
        Legend
      </p>
      {items.map(({ color, label, shape }) => (
        <div key={label} className="flex items-center gap-2">
          {shape === 'rect' ? (
            <div
              className="w-4 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: color }}
            />
          ) : shape === 'circle' ? (
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
          ) : shape === 'dashed' ? (
            <div
              className="w-4 h-0.5 flex-shrink-0"
              style={{ backgroundImage: `repeating-linear-gradient(to right, ${color} 0, ${color} 3px, transparent 3px, transparent 6px)` }}
            />
          ) : (
            <div className="w-4 h-0.5 flex-shrink-0" style={{ backgroundColor: color }} />
          )}
          <span style={{ color: 'var(--color-text-secondary)' }}>{label}</span>
        </div>
      ))}
    </div>
  )
}
