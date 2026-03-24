import { useParams, useLocation, Link } from 'react-router-dom'
import { useOntology } from '@/hooks/useOntology'
import { Home, ChevronRight } from 'lucide-react'

export default function TopBar() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const location = useLocation()
  const { data: ontology } = useOntology(ontologyId)

  const pathSegments = location.pathname.split('/').filter(Boolean)
  const currentPage = pathSegments[pathSegments.length - 1]
  const pageLabel = currentPage && currentPage !== ontologyId
    ? currentPage.charAt(0).toUpperCase() + currentPage.slice(1)
    : null

  return (
    <header
      className="h-12 border-b flex items-center px-4 gap-2 flex-shrink-0"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
    >
      <Link
        to="/"
        className="flex items-center gap-1 text-sm hover:opacity-80"
        style={{ color: 'var(--color-text-secondary)' }}
      >
        <Home size={14} />
        <span>Ontologies</span>
      </Link>

      {ontology && (
        <>
          <ChevronRight size={14} style={{ color: 'var(--color-text-muted)' }} />
          <Link
            to={`/${ontologyId}/graph`}
            className="text-sm font-medium hover:opacity-80"
            style={{ color: 'var(--color-text-primary)' }}
          >
            {ontology.name}
          </Link>
        </>
      )}

      {pageLabel && ontologyId && (
        <>
          <ChevronRight size={14} style={{ color: 'var(--color-text-muted)' }} />
          <span className="text-sm capitalize" style={{ color: 'var(--color-text-secondary)' }}>
            {pageLabel}
          </span>
        </>
      )}
    </header>
  )
}
