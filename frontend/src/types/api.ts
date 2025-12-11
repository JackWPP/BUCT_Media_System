/**
 * API 相关类型定义
 */

export interface ApiResponse<T = any> {
  data: T
  message?: string
}

export interface ApiError {
  detail: string
  status?: number
}

export interface PaginationParams {
  skip?: number
  limit?: number
}
