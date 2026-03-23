export type SourceType = 'jdbc' | 'api' | 'stream' | 'file'

export interface JDBCConfig {
  url: string
  driver: string
  username: string
  password: string
  query: string
  batch_size: number
}

export interface APIConfig {
  endpoint: string
  method: 'GET' | 'POST'
  headers: Record<string, string>
  params: Record<string, unknown>
  auth_type: 'none' | 'bearer' | 'basic' | 'api_key'
  auth_token?: string
  pagination_type: 'none' | 'page' | 'cursor' | 'offset'
  records_path?: string
}

export interface StreamConfig {
  bootstrap_servers: string
  topic: string
  consumer_group: string
  schema_registry_url?: string
  value_format: 'json' | 'avro' | 'protobuf'
}

export interface PropertyMapping {
  source_field: string
  property_iri: string
  property_type: 'data' | 'object'
  datatype?: string
  language?: string
  transform?: string
}

export interface BackingSource {
  id: string
  ontology_id: string
  name: string
  source_type: SourceType
  concept_iri: string
  iri_template: string
  property_mappings: PropertyMapping[]
  jdbc_config?: JDBCConfig
  api_config?: APIConfig
  stream_config?: StreamConfig
  is_active: boolean
  created_at: string
  updated_at: string
  last_synced_at?: string
}

export interface BackingSourceCreate {
  name: string
  source_type: SourceType
  concept_iri: string
  iri_template: string
  property_mappings?: PropertyMapping[]
  jdbc_config?: JDBCConfig
  api_config?: APIConfig
  stream_config?: StreamConfig
}

export interface BackingSourceUpdate {
  name?: string
  concept_iri?: string
  iri_template?: string
  property_mappings?: PropertyMapping[]
  jdbc_config?: JDBCConfig
  api_config?: APIConfig
  stream_config?: StreamConfig
  is_active?: boolean
}
