import request from './index'

/**
 * 批量导入相关 API
 */

/** 导入请求 */
export interface ImportRequest {
  json_path: string
  image_folder?: string
}

/** 导入响应 */
export interface ImportResponse {
  total_count: number
  imported_count: number
  skipped_count: number
  error_count: number
  errors: string[]
  message: string
}

/** 验证响应 */
export interface ValidateResponse {
  path: string
  exists: boolean
  is_file: boolean
  is_directory: boolean
  json_files_count: number
  json_files: string[]
}

/**
 * 批量导入照片
 */
export function importPhotos(data: ImportRequest) {
  return request.post<ImportResponse>('/api/v1/photos/import', data)
}

/**
 * 验证导入路径
 */
export function validateImportPath(jsonPath: string) {
  return request.get<ValidateResponse>('/api/v1/photos/import/validate', {
    params: { json_path: jsonPath }
  })
}
