import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppShell from '@/components/layout/AppShell'
import { DatasetProvider } from '@/contexts/DatasetContext'
import HomePage from '@/pages/HomePage'
import MCPDebugPage from '@/pages/MCPDebugPage'
import GraphPage from '@/pages/ontology/GraphPage'
import SchemaPage from '@/pages/ontology/SchemaPage'
import SPARQLPage from '@/pages/ontology/SPARQLPage'
import ImportPage from '@/pages/ontology/ImportPage'
import MergePage from '@/pages/ontology/MergePage'
import ReasonerPage from '@/pages/ontology/ReasonerPage'
import SourcesPage from '@/pages/ontology/SourcesPage'

export default function App() {
  return (
    <DatasetProvider>
    <BrowserRouter>
      <Routes>
        {/* Home — no shell */}
        <Route path="/" element={<HomePage />} />

        {/* MCP Debug — no shell */}
        <Route path="/mcp-debug" element={<MCPDebugPage />} />

        {/* Ontology routes — wrapped in AppShell */}
        <Route
          path="/:ontologyId/*"
          element={
            <AppShell>
              <Routes>
                <Route path="graph" element={<GraphPage />} />
                <Route path="schema" element={<SchemaPage />} />
                <Route path="sparql" element={<SPARQLPage />} />
                <Route path="import" element={<ImportPage />} />
                <Route path="merge" element={<MergePage />} />
                <Route path="reasoner" element={<ReasonerPage />} />
                <Route path="sources" element={<SourcesPage />} />
                {/* Default redirect to graph */}
                <Route path="" element={<GraphPage />} />
              </Routes>
            </AppShell>
          }
        />
      </Routes>
    </BrowserRouter>
    </DatasetProvider>
  )
}
