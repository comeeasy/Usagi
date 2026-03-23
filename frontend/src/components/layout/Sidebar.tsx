// TODO: 좌측 내비게이션 링크 목록
// 온톨로지 선택기, 페이지 내비게이션 링크 (Graph/Entities/Relations/SPARQL/...)
// lucide-react 아이콘 사용

import { useParams } from 'react-router-dom'

export default function Sidebar() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <aside className="w-64 bg-bg-surface border-r border-border">
      {/* TODO: nav links for ontologyId={ontologyId} */}
    </aside>
  )
}
