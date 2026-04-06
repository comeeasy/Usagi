// Ontology CRUD API client

import { API_BASE_URL, ApiError, apiFetch, apiGet, apiPost, apiPut, apiDelete } from './client'

function detailFromFastApiBody(body: unknown): string | undefined {
  if (body == null || typeof body !== 'object') return undefined
  const d = (body as { detail?: unknown }).detail
  if (typeof d === 'string') return d
  if (d && typeof d === 'object' && 'message' in d) return String((d as { message: string }).message)
  return undefined
}
import type { Ontology, OntologyCreate, OntologyUpdate, PaginatedResponse } from '@/types/ontology'

// Backend returns {label, iri, stats:{concepts,individuals,object_properties,data_properties}}
// Frontend types use {name, base_iri, stats:{class_count,individual_count,property_count,triple_count}}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapOntology(data: any): Ontology {
  const s = data.stats ?? {}
  const stats = {
    class_count: s.class_count ?? s.concepts ?? 0,
    individual_count: s.individual_count ?? s.individuals ?? 0,
    property_count: s.property_count ?? ((s.object_properties ?? 0) + (s.data_properties ?? 0)),
    triple_count: s.triple_count ?? 0,
  }
  return { ...data, name: data.label ?? data.name, base_iri: data.iri ?? data.base_iri, stats }
}

export function listOntologies(params?: { page?: number; pageSize?: number; dataset?: string }): Promise<PaginatedResponse<Ontology>> {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.pageSize) qs.set('page_size', String(params.pageSize))
  if (params?.dataset) qs.set('dataset', params.dataset)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiGet(`/ontologies${query}`).then((res: PaginatedResponse<Ontology>) => ({
    ...res,
    items: res.items.map(mapOntology),
  }))
}

export function getOntology(id: string, dataset?: string): Promise<Ontology> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiGet(`/ontologies/${id}${qs}`).then(mapOntology)
}

export function createOntology(data: OntologyCreate, dataset?: string): Promise<Ontology> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies${qs}`, {
    label: data.name,
    iri: data.base_iri,
    description: data.description,
    version: data.version,
  }).then(mapOntology)
}

export function updateOntology(id: string, data: OntologyUpdate, dataset?: string): Promise<Ontology> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPut(`/ontologies/${id}${qs}`, {
    label: data.name,
    description: data.description,
    version: data.version,
  }).then(mapOntology)
}

export function deleteOntology(id: string, dataset?: string): Promise<void> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiDelete(`/ontologies/${id}${qs}`)
}

export function syncOntology(id: string, dataset?: string): Promise<{ tbox_count: number; abox_count: number; elapsed_seconds: number }> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${id}/sync${qs}`, {})
}

export interface SubgraphData {
  nodes: Array<{ data: { id: string; label: string; kind: string; iri: string }; classes?: string }>
  edges: Array<{ data: { id: string; source: string; target: string; label: string; kind: string }; classes?: string }>
}

export function getSubgraph(
  ontologyId: string,
  params: { rootIris?: string[]; depth?: number; includeIndividuals?: boolean; dataset?: string },
): Promise<SubgraphData> {
  const qs = params.dataset ? `?dataset=${params.dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/subgraph${qs}`, {
    entity_iris: params.rootIris ?? [],
    depth: params.depth ?? 2,
  }).then((raw: { nodes: { iri: string; label: string; kind: string }[]; edges: { source: string; target: string; propertyIri: string; propertyLabel: string }[] }) => ({
    nodes: raw.nodes.map((n) => ({
      data: { id: n.iri, label: n.label, kind: n.kind, iri: n.iri },
      classes: n.kind === 'concept' ? 'concept' : 'individual',
    })),
    edges: raw.edges.map((e) => {
      const isSubclass = e.propertyIri === 'SUBCLASS_OF' || e.propertyIri === 'TYPE'
      return {
        data: {
          id: `${e.source}-${e.propertyIri}-${e.target}`,
          source: e.source,
          target: e.target,
          label: (() => {
            const raw = e.propertyLabel ?? e.propertyIri
            if (!raw || raw === 'RELATION' || raw === 'TYPE' || raw === 'SUBCLASS_OF') {
              const iri = e.propertyIri
              if (iri.includes('#')) return iri.split('#').at(-1) ?? iri
              if (iri.includes('/')) return iri.split('/').at(-1) ?? iri
              return iri
            }
            return raw
          })(),
          kind: isSubclass ? 'subclass' : 'object',
        },
        classes: isSubclass ? 'subclass' : 'object-property',
      }
    }),
  }))
}

export type ImportResult = {
  message: string
  triples_imported: number
  graph_iri?: string
  format?: string
  /** 파일 import 시 서버가 측정한 단계별 ms (read / parse / store / total) */
  timing_ms?: Record<string, number>
}

/** TTL 등 파일 업로드 진행 (브라우저 → API 게이트웨이 구간) */
export type ImportFileProgress =
  | { phase: 'upload'; loaded: number; total: number }
  | { phase: 'server' }

/**
 * 파일 import — XMLHttpRequest로 업로드 진행률을 알 수 있음. 완료 후 서버 처리 구간은 phase=server.
 */
export function importOntologyFile(
  ontologyId: string,
  file: File,
  dataset?: string,
  onProgress?: (p: ImportFileProgress) => void,
): Promise<ImportResult> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  const url = `${API_BASE_URL}/ontologies/${ontologyId}/import/file${qs}`

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)

    xhr.upload.addEventListener('progress', (ev) => {
      if (ev.lengthComputable) {
        onProgress?.({ phase: 'upload', loaded: ev.loaded, total: ev.total })
      }
    })
    xhr.upload.addEventListener('load', () => {
      onProgress?.({ phase: 'server' })
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText || '{}') as {
            imported: number
            graph_iri: string
            format: string
            timing_ms?: Record<string, number>
          }
          resolve({
            message: `Imported ${res.imported.toLocaleString()} triples`,
            triples_imported: res.imported,
            graph_iri: res.graph_iri,
            format: res.format,
            timing_ms: res.timing_ms,
          })
        } catch {
          reject(new Error('Invalid JSON from import response'))
        }
        return
      }
      let parsed: unknown
      try {
        parsed = JSON.parse(xhr.responseText || '{}')
      } catch {
        parsed = {}
      }
      const detail = detailFromFastApiBody(parsed)
      reject(new ApiError(xhr.status, xhr.statusText, detail))
    })

    xhr.addEventListener('error', () => {
      reject(new Error('Network error during import'))
    })

    xhr.open('POST', url)
    xhr.send(form)
  })
}

export function importOntologyUrl(
  ontologyId: string,
  url: string,
  dataset?: string,
): Promise<ImportResult> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/import/url${qs}`, { url }).then(
    (res: { imported: number; graph_iri: string; format: string }) => ({
      message: `Imported ${res.imported.toLocaleString()} triples`,
      triples_imported: res.imported,
      graph_iri: res.graph_iri,
      format: res.format,
    }),
  )
}

export function importOntologyStandard(
  ontologyId: string,
  name: string,
  dataset?: string,
): Promise<ImportResult> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/import/standard${qs}`, { name }).then(
    (res: { imported: number; graph_iri: string; format: string }) => ({
      message: `Imported ${res.imported.toLocaleString()} triples`,
      triples_imported: res.imported,
      graph_iri: res.graph_iri,
      format: res.format,
    }),
  )
}

/** @deprecated Use importOntologyFile / importOntologyUrl / importOntologyStandard */
export function importOntology(
  ontologyId: string,
  data: { format: string; content?: string; url?: string; file_name?: string },
): Promise<{ message: string; triples_imported?: number }> {
  if (data.url) return importOntologyUrl(ontologyId, data.url)
  if (data.content) return Promise.reject(new Error('importOntology: use importOntologyFile with a File object instead'))
  return Promise.reject(new Error('importOntology: url or content required'))
}

export interface ConflictItem {
  iri: string
  conflict_type: 'label' | 'domain' | 'range' | 'superClass'
  target_value: string
  source_value: string
}

export interface ConflictResolution {
  iri: string
  conflict_type: 'label' | 'domain' | 'range' | 'superClass'
  choice: 'keep-target' | 'keep-source' | 'merge-both'
}

export function previewMerge(
  targetId: string,
  sourceId: string,
  dataset?: string,
): Promise<{ conflicts: ConflictItem[]; conflict_count: number; auto_mergeable_count: number }> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${targetId}/merge/preview${qs}`, { source_ontology_id: sourceId })
}

export function mergeOntologies(
  targetId: string,
  sourceId: string,
  resolutions: ConflictResolution[] = [],
  dataset?: string,
): Promise<{ merged: boolean; triple_count: number }> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${targetId}/merge${qs}`, { source_ontology_id: sourceId, resolutions })
}

// ── Datasets API ────────────────────────────────────────────────────────────

export interface DatasetInfo {
  name: string
  type: string
}

export function listDatasets(): Promise<DatasetInfo[]> {
  return apiGet('/datasets')
}

export function createDataset(name: string, dbType = 'TDB2'): Promise<{ name: string; db_type: string; status: string }> {
  return apiPost('/datasets', { name, db_type: dbType })
}

export function deleteDataset(name: string): Promise<void> {
  return apiDelete(`/datasets/${name}`)
}
