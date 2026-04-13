import { BrowserRouter, Routes, Route, useParams } from 'react-router-dom'
import AppShell from '@/components/layout/AppShell'
import { DatasetProvider } from '@/contexts/DatasetContext'
import { NamedGraphsProvider } from '@/contexts/NamedGraphsContext'
import HomePage from '@/pages/HomePage'
import MCPDebugPage from '@/pages/MCPDebugPage'
import GraphPage from '@/pages/ontology/GraphPage'
import SchemaPage from '@/pages/ontology/SchemaPage'
import SPARQLPage from '@/pages/ontology/SPARQLPage'
import ImportPage from '@/pages/ontology/ImportPage'
import ReasonerPage from '@/pages/ontology/ReasonerPage'
import SourcesPage from '@/pages/ontology/SourcesPage'

function OntologyShell() {
  const { ontologyId } = useParams<{ ontologyId: string }>()
  return (
    <NamedGraphsProvider key={ontologyId}>
      <AppShell>
        <Routes>
          <Route path="graph" element={<GraphPage />} />
          <Route path="schema" element={<SchemaPage />} />
          <Route path="sparql" element={<SPARQLPage />} />
          <Route path="import" element={<ImportPage />} />
          <Route path="reasoner" element={<ReasonerPage />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="" element={<GraphPage />} />
        </Routes>
      </AppShell>
    </NamedGraphsProvider>
  )
}

export default function App() {
  return (
    <DatasetProvider>
    <BrowserRouter>
      <Routes>
        {/* Home — no shell */}
        <Route path="/" element={<HomePage />} />

        {/* MCP Debug — no shell */}
        <Route path="/mcp-debug" element={<MCPDebugPage />} />

        {/* Ontology routes — wrapped in AppShell + NamedGraphsProvider per ontology */}
        <Route path="/:ontologyId/*" element={<OntologyShell />} />
      </Routes>
    </BrowserRouter>
    </DatasetProvider>
  )
}
