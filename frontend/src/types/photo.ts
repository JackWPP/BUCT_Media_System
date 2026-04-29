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
  classifications: Record<string, TaxonomyValue>
  uploader_name: string | null
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
  gallery_series?: string
  gallery_year?: string
  photo_type?: string
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
  gallery_series?: string | null
  gallery_year?: string | null
  photo_type?: string | null
  status?: string | null
  search?: string
  tag?: string | null
  sortBy?: string
  sortOrder?: string
}
