// TODO: SourceList + SourceConfigForm + MappingEditor 조합
// Backing Source CRUD, 동기화 트리거 버튼

import { useParams } from 'react-router-dom'

export default function SourcesPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>SourcesPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
