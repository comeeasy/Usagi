// TODO: 파일 업로드, URL 임포트, 표준 온톨로지 선택 UI
// 임포트 진행 상태 표시

import { useParams } from 'react-router-dom'

export default function ImportPage() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <div className="p-4">
      <h1>ImportPage</h1>
      {/* TODO: ontologyId={ontologyId} */}
    </div>
  )
}
