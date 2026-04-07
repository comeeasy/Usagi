import { NavLink, useParams } from 'react-router-dom'

const tabs = [
  { path: 'graph', label: 'Graph' },
  { path: 'entities', label: 'Entities' },
  { path: 'relations', label: 'Relations' },
  { path: 'sparql', label: 'SPARQL' },
  { path: 'sources', label: 'Sources' },
  { path: 'merge', label: 'Merge' },
  { path: 'reasoner', label: 'Reasoner' },
]

export default function OntologyTabs() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  if (!ontologyId) return null

  return (
    <nav
      className="flex border-b px-4 overflow-x-auto flex-shrink-0"
      style={{ borderColor: 'var(--color-border)' }}
    >
      {tabs.map(({ path, label }) => (
        <NavLink
          key={path}
          to={`/${ontologyId}/${path}`}
          className={({ isActive }) =>
            `px-4 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
              isActive
                ? 'border-current font-medium'
                : 'border-transparent'
            }`
          }
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
