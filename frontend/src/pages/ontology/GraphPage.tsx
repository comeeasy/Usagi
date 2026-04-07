import { useState } from 'react'
import { useParams } from 'react-router-dom'
import OntologyTabs from '@/components/layout/OntologyTabs'
import NamedGraphList from '@/components/graph/NamedGraphList'
import ImportPanel from '@/components/graph/ImportPanel'

export default function GraphPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  const [showImport, setShowImport] = useState(false)

  return (
    <div className="flex flex-col h-full">
      <OntologyTabs />

      <div className="flex flex-1 overflow-hidden">
        {/* Named graphs list */}
        <div className={`flex flex-col overflow-hidden transition-all ${showImport ? 'flex-1' : 'w-full'}`}>
          <NamedGraphList
            ontologyId={ontologyId!}
            onImportClick={() => setShowImport(true)}
          />
        </div>

        {/* Import panel */}
        {showImport && (
          <div className="w-96 shrink-0 flex flex-col overflow-hidden">
            <ImportPanel
              ontologyId={ontologyId!}
              onClose={() => setShowImport(false)}
            />
          </div>
        )}
      </div>
    </div>
  )
}
