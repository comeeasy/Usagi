import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

const PREFIX_MAP: Record<string, string> = {
  'http://www.w3.org/2002/07/owl#': 'owl:',
  'http://www.w3.org/2000/01/rdf-schema#': 'rdfs:',
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf:',
  'http://www.w3.org/2001/XMLSchema#': 'xsd:',
  'http://schema.org/': 'schema:',
  'http://xmlns.com/foaf/0.1/': 'foaf:',
  'http://purl.org/dc/terms/': 'dcterms:',
  'http://purl.org/dc/elements/1.1/': 'dc:',
}

function shortenIRI(iri: string): string {
  for (const [prefix, short] of Object.entries(PREFIX_MAP)) {
    if (iri.startsWith(prefix)) {
      return short + iri.slice(prefix.length)
    }
  }
  // Try to shorten by taking last segment
  const hashIdx = iri.lastIndexOf('#')
  if (hashIdx !== -1) return '...' + iri.slice(hashIdx)
  const slashIdx = iri.lastIndexOf('/')
  if (slashIdx !== -1 && slashIdx < iri.length - 1) {
    return '...' + iri.slice(slashIdx)
  }
  return iri
}

interface IRIBadgeProps {
  iri: string
  onClick?: (iri: string) => void
  showCopy?: boolean
}

export default function IRIBadge({ iri, onClick, showCopy = false }: IRIBadgeProps) {
  const [copied, setCopied] = useState(false)
  const short = shortenIRI(iri)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(iri).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <span
      className="inline-flex items-center gap-1 font-mono text-xs px-1.5 py-0.5 rounded cursor-pointer group"
      style={{
        backgroundColor: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-info)',
      }}
      title={iri}
      onClick={() => onClick?.(iri)}
    >
      {short}
      {showCopy && (
        <button
          className="opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={handleCopy}
          title="Copy IRI"
        >
          {copied ? <Check size={10} style={{ color: 'var(--color-success)' }} /> : <Copy size={10} />}
        </button>
      )}
    </span>
  )
}
