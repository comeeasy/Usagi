import { http, HttpResponse } from 'msw'

const BASE = '/api/v1'

export const mockOntology = {
  id: 'test-ont-uuid',
  name: 'Test Ontology',
  description: 'A test ontology',
  base_iri: 'https://test.example.org/onto',
  version: '1.0.0',
  created_at: '2026-03-25T00:00:00Z',
  updated_at: '2026-03-25T00:00:00Z',
  stats: { class_count: 2, individual_count: 1, property_count: 1, triple_count: 10 },
}

export const mockConcept = {
  iri: 'https://test.example.org/onto#Person',
  ontology_id: 'test-ont-uuid',
  label: 'Person',
  comment: 'A human being',
  super_classes: [],
  individual_count: 1,
}

export const mockObjectProperty = {
  iri: 'https://test.example.org/onto#hasParent',
  ontology_id: 'test-ont-uuid',
  label: 'hasParent',
  comment: 'Relates a person to their parent',
  domain: ['https://test.example.org/onto#Person'],
  range: ['https://test.example.org/onto#Person'],
  characteristics: [],
  inverseOf: '',
}

export const mockDataProperty = {
  iri: 'https://test.example.org/onto#age',
  ontology_id: 'test-ont-uuid',
  label: 'age',
  comment: 'The age of a person',
  domain: ['https://test.example.org/onto#Person'],
  range: ['xsd:integer'],
  isFunctional: false,
}

export const handlers = [
  // Ontologies
  http.get(`${BASE}/ontologies`, () =>
    HttpResponse.json({ items: [mockOntology], total: 1, page: 1, page_size: 20 }),
  ),
  http.get(`${BASE}/ontologies/:id`, ({ params }) =>
    HttpResponse.json({ ...mockOntology, id: params.id }),
  ),
  http.post(`${BASE}/ontologies`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockOntology, ...body }, { status: 201 })
  }),
  http.put(`${BASE}/ontologies/:id`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockOntology, id: params.id, ...body })
  }),
  http.delete(`${BASE}/ontologies/:id`, () => new HttpResponse(null, { status: 204 })),

  // Concepts
  http.get(`${BASE}/ontologies/:id/concepts`, () =>
    HttpResponse.json({ items: [mockConcept], total: 1, page: 1, page_size: 20 }),
  ),
  http.post(`${BASE}/ontologies/:id/concepts`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockConcept, ...body }, { status: 201 })
  }),

  // Individuals
  http.get(`${BASE}/ontologies/:id/individuals`, () =>
    HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 }),
  ),

  // Properties (Relations)
  http.get(`${BASE}/ontologies/:id/properties/object`, () =>
    HttpResponse.json({ items: [mockObjectProperty], total: 1, page: 1, page_size: 20 }),
  ),
  http.get(`${BASE}/ontologies/:id/properties/data`, () =>
    HttpResponse.json({ items: [mockDataProperty], total: 1, page: 1, page_size: 20 }),
  ),
  http.post(`${BASE}/ontologies/:id/properties/object`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockObjectProperty, ...body }, { status: 201 })
  }),
  http.post(`${BASE}/ontologies/:id/properties/data`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({ ...mockDataProperty, ...body }, { status: 201 })
  }),

  // SPARQL
  http.post(`${BASE}/ontologies/:id/sparql`, async ({ request }) => {
    const body = await request.json() as { query?: string }
    const q = (body.query ?? '').toUpperCase()
    if (q.includes('UPDATE') || q.includes('INSERT') || q.includes('DELETE')) {
      return HttpResponse.json({ error: 'Mutating queries are not allowed' }, { status: 403 })
    }
    return HttpResponse.json({
      variables: ['c'],
      bindings: [{ c: { type: 'uri', value: 'https://test.example.org/onto#Person' } }],
    })
  }),
]
