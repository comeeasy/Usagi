import { NavLink, useParams, useNavigate } from 'react-router-dom'
import {
  Network,
  Users,
  GitBranch,
  Code2,
  Upload,
  Merge,
  Brain,
  Database,
  Bug,
  Box,
} from 'lucide-react'
import { useOntologies } from '@/hooks/useOntology'
import DatasetSelector from './DatasetSelector'

const navItems = [
  { path: 'graph', label: 'Graph', icon: Network },
  { path: 'entities', label: 'Entities', icon: Users },
  { path: 'relations', label: 'Relations', icon: GitBranch },
  { path: 'sparql', label: 'SPARQL', icon: Code2 },
  { path: 'sources', label: 'Sources', icon: Database },
  { path: 'import', label: 'Import', icon: Upload },
  { path: 'merge', label: 'Merge', icon: Merge },
  { path: 'reasoner', label: 'Reasoner', icon: Brain },
]

export default function Sidebar() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const navigate = useNavigate()
  const { data } = useOntologies(1, 50)

  return (
    <aside
      className="w-56 flex flex-col flex-shrink-0 border-r overflow-y-auto"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Logo */}
      <div
        className="h-12 flex items-center px-4 gap-2 border-b flex-shrink-0"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <Box size={18} style={{ color: 'var(--color-primary)' }} />
        <span className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          Ontology Platform
        </span>
      </div>

      {/* Dataset selector */}
      <DatasetSelector />

      {/* Ontology selector */}
      <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <label className="text-xs mb-1 block" style={{ color: 'var(--color-text-muted)' }}>
          Ontology
        </label>
        <select
          className="w-full text-xs px-2 py-1.5 rounded border"
          style={{
            backgroundColor: 'var(--color-bg-elevated)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-primary)',
          }}
          value={ontologyId ?? ''}
          onChange={(e) => {
            if (e.target.value) navigate(`/${e.target.value}/graph`)
          }}
        >
          <option value="">Select ontology...</option>
          {data?.items.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      </div>

      {/* Nav links */}
      {ontologyId && (
        <nav className="flex flex-col py-2 flex-1">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={`/${ontologyId}/${path}`}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-4 py-2 text-sm transition-colors ${
                  isActive ? 'font-medium' : ''
                }`
              }
              style={({ isActive }) => ({
                backgroundColor: isActive ? 'var(--color-bg-elevated)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              })}
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>
      )}

      {/* Bottom links */}
      <div className="border-t py-2" style={{ borderColor: 'var(--color-border)' }}>
        <NavLink
          to="/mcp-debug"
          className="flex items-center gap-2.5 px-4 py-2 text-sm"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
          })}
        >
          <Bug size={15} />
          MCP Debug
        </NavLink>
      </div>
    </aside>
  )
}
