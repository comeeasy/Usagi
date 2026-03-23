// TODO: GraphCanvas + GraphControls + GraphLegend + NodeDetailPanel 조합
// useParams()로 ontologyId 추출, useSubgraph hook으로 그래프 데이터 조회

import { useParams } from 'react-router-dom'

export default function GraphPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>GraphPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
