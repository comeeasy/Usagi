// Ontology CRUD API client

import { apiFetch, apiGet, apiPost, apiPut, apiDelete } from './client'
import type { Ontology, OntologyCreate, OntologyUpdate, PaginatedResponse } from '@/types/ontology'

// Backend returns {label, iri} but frontend types use {name, base_iri}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapOntology(data: any): Ontology {
  return { ...data, name: data.label ?? data.name, base_iri: data.iri ?? data.base_iri }
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

export function importOntologyFile(
  ontologyId: string,
  file: File,
  dataset?: string,
): Promise<{ message: string; triples_imported?: number }> {
  const form = new FormData()
  form.append('file', file)
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiFetch<{ imported: number }>(`/ontologies/${ontologyId}/import/file${qs}`, {
    method: 'POST',
    body: form,
  }).then((res) => ({ message: `Imported ${res.imported} triples`, triples_imported: res.imported }))
}

export function importOntologyUrl(
  ontologyId: string,
  url: string,
  dataset?: string,
): Promise<{ message: string; triples_imported?: number }> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/import/url${qs}`, { url })
    .then((res: { imported: number }) => ({ message: `Imported ${res.imported} triples`, triples_imported: res.imported }))
}

export function importOntologyStandard(
  ontologyId: string,
  name: string,
  dataset?: string,
): Promise<{ message: string; triples_imported?: number }> {
  const qs = dataset ? `?dataset=${dataset}` : ''
  return apiPost(`/ontologies/${ontologyId}/import/standard${qs}`, { name })
    .then((res: { imported: number }) => ({ message: `Imported ${res.imported} triples`, triples_imported: res.imported }))
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
