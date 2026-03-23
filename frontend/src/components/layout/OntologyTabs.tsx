// TODO: 서브 탭 (graph/entities/relations/sparql/import/merge/reasoner/sources)
// 현재 활성 탭 하이라이트, react-router-dom NavLink 사용

import { useParams } from 'react-router-dom'

export default function OntologyTabs() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <nav className="flex border-b border-border">
      {/* TODO: tab links for ontologyId={ontologyId} */}
    </nav>
  )
}
