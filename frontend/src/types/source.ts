export type SourceType = 'jdbc' | 'api' | 'stream' | 'csv-file'

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

export interface CSVConfig {
  file_name?: string
  delimiter: ',' | ';' | '\t' | '|'
  has_header: boolean
  primary_key_field: string
  encoding: 'utf-8' | 'utf-16' | 'latin-1'
  skip_rows?: number
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
  label: string
  source_type: SourceType
  concept_iri: string
  iri_template: string
  property_mappings: PropertyMapping[]
  config?: JDBCConfig | APIConfig | StreamConfig | CSVConfig
  status: 'active' | 'paused' | 'error'
  last_sync_at?: string
}

export interface BackingSourceCreate {
  label: string
  source_type: SourceType
  concept_iri: string
  iri_template: string
  property_mappings?: PropertyMapping[]
  config?: JDBCConfig | APIConfig | StreamConfig | CSVConfig
}

export interface BackingSourceUpdate {
  label?: string
  concept_iri?: string
  iri_template?: string
  property_mappings?: PropertyMapping[]
  config?: JDBCConfig | APIConfig | StreamConfig | CSVConfig
  status?: 'active' | 'paused' | 'error'
}

export interface UploadResult {
  file_name: string
  headers: string[]
  row_count: number
  rows_read: number
  triples_inserted: number
  neo4j_nodes_upserted: number
  named_graph: string
}
