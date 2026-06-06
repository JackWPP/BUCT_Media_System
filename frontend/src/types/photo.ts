/**
 * Photo-related types.
 */

export interface TaxonomyValue {
  facet_key: string
  facet_name: string
  node_id: number
  node_key: string
  node_name: string
  path: string[]
}

export interface Photo {
  id: string
  uploader_id: string
  filename: string
  original_path: string
  processed_path: string | null
  thumb_path: string | null
  width: number | null
  height: number | null
  file_size: number | null
  mime_type: string | null
  season: string | null
  category: string | null
  campus: string | null
  description: string | null
  exif_data: Record<string, any> | null
  status: string
  processing_status: string
  created_at: string
  updated_at: string
  captured_at: string | null
  published_at: string | null
  tags: string[]
  free_tags: string[]
  classifications: Record<string, TaxonomyValue | TaxonomyValue[]>
  uploader_name: string | null
  uploader_student_id: string | null
}

export interface PhotoUploadResponse {
  id: string
  filename: string
  original_path: string
  thumb_path: string | null
  width: number | null
  height: number | null
  status: string
  message: string
}

export interface PhotoUpdate {
  description?: string
  season?: string
  category?: string
  campus?: string
  status?: string
}

export interface SearchInterpretation {
  facet_filters: Record<string, string>
  keywords: string[]
  original_query: string
  method: 'rule' | 'ai' | 'fallback'
  confidence: number
  explanation: string | null
}

export interface PhotoListParams {
  skip?: number
  limit?: number
  status?: string
  season?: string
  category?: string
  campus?: string
  building?: string
  source_type?: string
  facility?: string
  landscape?: string
  natural_phenomenon?: string
  technique?: string
  animal?: string
  plant?: string
  gallery_series?: string
  gallery_year?: string
  award_level?: string
  photo_type?: string
  documentary_topic?: string
  search?: string
  tag?: string
  sort_by?: string
  sort_order?: string
  smart?: boolean
}

export interface PhotoListResponse {
  items: Photo[]
  total: number
  page: number
  page_size: number
  search_interpretation?: SearchInterpretation | null
}

export interface PhotoFilters {
  season?: string | null
  category?: string | null
  campus?: string | null
  building?: string | null
  source_type?: string | null
  facility?: string | null
  landscape?: string | null
  natural_phenomenon?: string | null
  technique?: string | null
  animal?: string | null
  plant?: string | null
  gallery_series?: string | null
  gallery_year?: string | null
  award_level?: string | null
  photo_type?: string | null
  documentary_topic?: string | null
  status?: string | null
  search?: string
  tag?: string | null
  sortBy?: string
  sortOrder?: string
}

export function firstTaxonomyValue(value: TaxonomyValue | TaxonomyValue[] | null | undefined): TaxonomyValue | null {
  if (!value) return null
  return Array.isArray(value) ? (value[0] || null) : value
}

export function taxonomyValueName(value: TaxonomyValue | TaxonomyValue[] | null | undefined): string {
  return firstTaxonomyValue(value)?.node_name || ''
}
