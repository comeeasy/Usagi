// TODO: 두 온톨로지 선택, 머지 전략 설정, 충돌 해소 UI

import { useParams } from 'react-router-dom'

export default function MergePage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>MergePage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
