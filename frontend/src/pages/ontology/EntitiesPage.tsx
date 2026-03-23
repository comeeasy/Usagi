// TODO: EntitySearchBar + EntityTable + EntityDetailPanel 조합
// Concept/Individual 탭 전환, useEntitySearch hook 사용

import { useParams } from 'react-router-dom'

export default function EntitiesPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>EntitiesPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
