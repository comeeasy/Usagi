// TODO: SPARQLEditor + SPARQLResultsTable 조합
// useSPARQL hook으로 쿼리 실행, 결과 테이블/JSON 전환

import { useParams } from 'react-router-dom'

export default function SPARQLPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>SPARQLPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
