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
  | 'xsd:langString'

export type ObjectPropertyCharacteristic =
  | 'Functional'
  | 'InverseFunctional'
  | 'Transitive'
  | 'Symmetric'
  | 'Asymmetric'
  | 'Reflexive'
  | 'Irreflexive'

export interface ObjectProperty {
  iri: string
  ontologyId: string
  label: string
  comment?: string
  domain: string[]            // Concept IRI 목록
  range: string[]             // Concept IRI 목록
  superProperties: string[]   // rdfs:subPropertyOf
  inverseOf?: string          // owl:inverseOf
  characteristics: ObjectPropertyCharacteristic[]
}

export interface DataProperty {
  iri: string
  ontologyId: string
  label: string
  comment?: string
  domain: string[]            // Concept IRI 목록
  range: XSDDatatype[]        // xsd:* 타입 목록
  superProperties: string[]
  isFunctional: boolean
}

export interface ObjectPropertyCreate {
  iri: string
  label: string
  comment?: string
  domain?: string[]
  range?: string[]
  superProperties?: string[]
  inverseOf?: string
  characteristics?: ObjectPropertyCharacteristic[]
}

export interface DataPropertyCreate {
  iri: string
  label: string
  comment?: string
  domain?: string[]
  range?: XSDDatatype[]
  superProperties?: string[]
  isFunctional?: boolean
}

export type PropertyCreate = ObjectPropertyCreate | DataPropertyCreate
