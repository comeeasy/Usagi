export interface PropertyRestriction {
  property_iri: string
  restriction_type: 'some' | 'all' | 'exactly' | 'min' | 'max'
  cardinality?: number
  filler_iri?: string
}

export interface Concept {
  iri: string
  label?: string
  comment?: string
  ontology_id: string
  parent_iris: string[]
  restrictions: PropertyRestriction[]
  is_deprecated: boolean
}

export interface ConceptCreate {
  iri: string
  label?: string
  comment?: string
  parent_iris?: string[]
  restrictions?: PropertyRestriction[]
}

export interface ConceptUpdate {
  label?: string
  comment?: string
  parent_iris?: string[]
  restrictions?: PropertyRestriction[]
  is_deprecated?: boolean
}
