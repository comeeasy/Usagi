// TODO:
// - BrowserRouter로 전체 앱 감싸기
// - Routes 정의:
//   / → HomePage
//   /:ontologyId/graph → GraphPage
//   /:ontologyId/entities → EntitiesPage
//   /:ontologyId/relations → RelationsPage
//   /:ontologyId/sparql → SPARQLPage
//   /:ontologyId/import → ImportPage
//   /:ontologyId/merge → MergePage
//   /:ontologyId/reasoner → ReasonerPage
//   /:ontologyId/sources → SourcesPage
//   /mcp-debug → MCPDebugPage
// - AppShell로 모든 라우트 감싸기 (홈 제외)

import { BrowserRouter, Routes, Route } from 'react-router-dom'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* TODO: implement routes */}
      </Routes>
    </BrowserRouter>
  )
}
