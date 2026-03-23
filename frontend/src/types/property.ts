export type XSDDatatype =
  | 'xsd:string'
  | 'xsd:integer'
  | 'xsd:decimal'
  | 'xsd:float'
  | 'xsd:double'
  | 'xsd:boolean'
  | 'xsd:date'
  | 'xsd:dateTime'
  | 'xsd:anyURI'

export type ObjectPropertyCharacteristic =
  | 'functional'
  | 'inverseFunctional'
  | 'transitive'
  | 'symmetric'
  | 'asymmetric'
  | 'reflexive'
  | 'irreflexive'

export interface ObjectProperty {
  iri: string
  label?: string
  comment?: string
  ontology_id: string
  domain_iri?: string
  range_iri?: string
  characteristics: ObjectPropertyCharacteristic[]
  inverse_of?: string
  is_deprecated: boolean
}

export interface DataProperty {
  iri: string
  label?: string
  comment?: string
  ontology_id: string
  domain_iri?: string
  range_datatype?: XSDDatatype
  is_functional: boolean
  is_deprecated: boolean
}

export interface ObjectPropertyCreate {
  iri: string
  label?: string
  comment?: string
  domain_iri?: string
  range_iri?: string
  characteristics?: ObjectPropertyCharacteristic[]
  inverse_of?: string
}

export interface DataPropertyCreate {
  iri: string
  label?: string
  comment?: string
  domain_iri?: string
  range_datatype?: XSDDatatype
  is_functional?: boolean
}

export type PropertyCreate = ObjectPropertyCreate | DataPropertyCreate
