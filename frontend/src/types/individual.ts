export interface DataPropertyValue {
  property_iri: string
  value: unknown
  datatype?: string
  language?: string
}

export interface ObjectPropertyValue {
  property_iri: string
  target_iri: string
}

export interface ProvenanceRecord {
  source_id: string
  source_type: string
  generated_at: string
  record_id?: string
  named_graph_iri?: string
}

export interface Individual {
  iri: string
  label?: string
  ontology_id: string
  types: string[]
  data_property_values: DataPropertyValue[]
  object_property_values: ObjectPropertyValue[]
  provenance: ProvenanceRecord[]
}

export interface IndividualCreate {
  iri: string
  label?: string
  types?: string[]
  data_property_values?: DataPropertyValue[]
  object_property_values?: ObjectPropertyValue[]
}

export interface IndividualUpdate {
  label?: string
  types?: string[]
  data_property_values?: DataPropertyValue[]
  object_property_values?: ObjectPropertyValue[]
}
