// TODO: RelationSearchBar + RelationTable + RelationDetailPanel 조합
// ObjectProperty/DataProperty 탭 전환

import { useParams } from 'react-router-dom'

export default function RelationsPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>RelationsPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
