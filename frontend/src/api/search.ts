/**
 * Enhanced search API - combines vector search with photo details
 */
import request from './index'

/** 搜索结果项 */
export interface SearchResult {
  photo_id: string
  score: number
  tags: string[]
  classifications: Record<string, string | null>
  // 扩展字段：完整照片信息
  photo?: {
    id: string
    filename: string
    width: number
    height: number
    thumb_url: string
    created_at: string
  }
}

/** 搜索响应 */
export interface SearchResponse {
  results: SearchResult[]
  total: number
  query_time_ms: number
  search_mode: 'vector' | 'keyword' | 'hybrid'
}

/** 搜索参数 */
export interface SearchParams {
  q: string
  limit?: number
  season?: string
  campus?: string
  building?: string
  gallery_series?: string
  gallery_year?: string
  award_level?: string
  photo_type?: string
}

/**
 * 向量搜索照片（公开接口，无需登录）
 */
export function searchPhotos(params: SearchParams): Promise<SearchResponse> {
  return request.get<SearchResponse>('/api/v1/search', { params })
}

/**
 * 智能搜索解释（用于展示搜索理解结果）
 */
export function interpretSearch(query: string): Promise<{
  facet_filters: Record<string, string>
  keywords: string[]
  original_query: string
  method: string
  confidence: number
}> {
  return request.post('/api/v1/photos/interpret-search', { query })
}
