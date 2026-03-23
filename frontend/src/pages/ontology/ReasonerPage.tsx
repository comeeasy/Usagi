// TODO: SubgraphSelector + 추론 실행 버튼 + ReasonerResults 조합
// useReasoner hook으로 추론 실행 및 polling

import { useParams } from 'react-router-dom'

export default function ReasonerPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>ReasonerPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
