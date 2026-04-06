export type RestrictionType =
  | 'someValuesFrom'
  | 'allValuesFrom'
  | 'hasValue'
  | 'minCardinality'
  | 'maxCardinality'
  | 'exactCardinality'

export interface PropertyRestriction {
  property_iri: string
  type: RestrictionType
  value: string        // 클래스 IRI 또는 리터럴
  cardinality?: number
}

export interface PropertyValue {
  predicate: string
  value: string
  value_type: 'uri' | 'literal'
  datatype?: string
  language?: string
}

export interface Concept {
  iri: string
  label?: string
  comment?: string
  ontology_id: string
  super_classes: string[]
  equivalent_classes: string[]
  disjoint_with: string[]
  restrictions: PropertyRestriction[]
  individual_count: number
  subclass_count: number
  properties: PropertyValue[]
  is_deprecated?: boolean
}

export interface ConceptCreate {
  iri: string
  label?: string
  comment?: string
  super_classes?: string[]
  equivalent_classes?: string[]
  disjoint_with?: string[]
  restrictions?: PropertyRestriction[]
}

export interface ConceptUpdate {
  label?: string
  comment?: string
  super_classes?: string[]
  equivalent_classes?: string[]
  disjoint_with?: string[]
  restrictions?: PropertyRestriction[]
  is_deprecated?: boolean
}
