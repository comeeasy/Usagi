// TODO: 온톨로지 제목 + 브레드크럼
// 현재 온톨로지 이름 표시, 페이지 경로 브레드크럼

import { useParams } from 'react-router-dom'

export default function TopBar() {
  const { ontologyId } = useParams<{ ontologyId: string }>()

  return (
    <header className="h-12 bg-bg-surface border-b border-border flex items-center px-4">
      {/* TODO: breadcrumb for ontologyId={ontologyId} */}
    </header>
  )
}
