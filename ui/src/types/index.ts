export interface SchemaField {
  name: string
  required: boolean
}

export interface Schema {
  fields: SchemaField[]
}

export interface CsvColumn {
  name: string
}

export interface UploadResponse {
  file_id: string
  has_header: boolean
}

export interface ColumnsResponse {
  columns: CsvColumn[]
}

export interface Suggestion {
  schema_field: string
  csv_column: string
  confidence: number
}

export interface SuggestMappingResponse {
  suggestions: Suggestion[]
}

export interface ValidateMappingResponse {
  is_valid: boolean
  errors: string[]
}

export interface SaveMappingResponse {
  id: string | number
  name: string
}

export interface SavedMappingItem {
  id: string | number
  name: string
}

export interface SavedMappingsResponse {
  items: SavedMappingItem[]
}

export interface SingleMappingResponse {
  id: string | number
  name: string
  mapping: Record<string, string>
}

export interface PreviewResponse {
  rows: string[][]
}
