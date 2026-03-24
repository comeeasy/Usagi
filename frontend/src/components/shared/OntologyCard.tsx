import { useNavigate } from 'react-router-dom'
import type { Ontology } from '@/types/ontology'
import { BookOpen, Users, GitBranch, Clock } from 'lucide-react'

interface OntologyCardProps {
  ontology: Ontology
  onClick?: (id: string) => void
}

export default function OntologyCard({ ontology, onClick }: OntologyCardProps) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (onClick) {
      onClick(ontology.id)
    } else {
      navigate(`/${ontology.id}/graph`)
    }
  }

  const updatedAt = new Date(ontology.updated_at).toLocaleDateString()

  return (
    <div
      className="p-4 rounded-lg border cursor-pointer transition-all hover:shadow-lg"
      style={{
        backgroundColor: 'var(--color-bg-surface)',
        borderColor: 'var(--color-border)',
      }}
      onClick={handleClick}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--color-primary)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--color-border)'
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-base" style={{ color: 'var(--color-text-primary)' }}>
            {ontology.name}
          </h3>
          <p
            className="text-xs mt-0.5 font-mono truncate max-w-xs"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {ontology.base_iri}
          </p>
        </div>
        {ontology.version && (
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: 'var(--color-bg-elevated)',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
            }}
          >
            v{ontology.version}
          </span>
        )}
      </div>

      {ontology.description && (
        <p className="text-sm mb-3 line-clamp-2" style={{ color: 'var(--color-text-secondary)' }}>
          {ontology.description}
        </p>
      )}

      <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--color-text-muted)' }}>
        <span className="flex items-center gap-1">
          <BookOpen size={12} />
          {ontology.stats.class_count} classes
        </span>
        <span className="flex items-center gap-1">
          <Users size={12} />
          {ontology.stats.individual_count} individuals
        </span>
        <span className="flex items-center gap-1">
          <GitBranch size={12} />
          {ontology.stats.property_count} properties
        </span>
        <span className="flex items-center gap-1 ml-auto">
          <Clock size={12} />
          {updatedAt}
        </span>
      </div>
    </div>
  )
}
