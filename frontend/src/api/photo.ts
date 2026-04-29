/**
 * Photo APIs.
 */
import request from './index'
import type {
  Photo,
  PhotoListParams,
  PhotoListResponse,
  PhotoUpdate,
  PhotoUploadResponse,
  SearchInterpretation,
} from '../types/photo'

export interface AIAnalysisTask {
  id: string
  photo_id: string
  requested_by_id: string | null
  reviewed_by_id: string | null
  provider: string
  model_id: string
  status: string
  prompt_version: string
  result_json: Record<string, any> | null
  error_message: string | null
  created_at: string
  updated_at: string
  completed_at: string | null
  applied_at: string | null
}

export interface AIApplyResponse {
  applied: boolean
  task: AIAnalysisTask
  unresolved_classifications: Record<string, string>
}

export function getPhotos(params?: PhotoListParams): Promise<PhotoListResponse> {
  return request({ url: '/api/v1/photos', method: 'get', params })
}

export function getPublicPhotos(params?: PhotoListParams): Promise<PhotoListResponse> {
  return request({ url: '/api/v1/photos/public', method: 'get', params })
}

export function getMySubmissions(params?: PhotoListParams): Promise<PhotoListResponse> {
  return request({ url: '/api/v1/photos/my-submissions', method: 'get', params })
}

export function interpretSearch(query: string): Promise<SearchInterpretation> {
  return request({ url: '/api/v1/photos/interpret-search', method: 'post', data: { query } })
}

export function getPhotoById(id: string): Promise<Photo> {
  return request({ url: `/api/v1/photos/${id}`, method: 'get' })
}

export function getPublicPhotoById(id: string): Promise<Photo> {
  return request({ url: `/api/v1/photos/public/${id}`, method: 'get' })
}

export function uploadPhoto(
  file: File,
  metadata: {
    description?: string
    season?: string
    category?: string
    campus?: string
  } = {},
  onProgress?: (progressEvent: any) => void,
): Promise<PhotoUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (metadata.description) formData.append('description', metadata.description)
  if (metadata.season) formData.append('season', metadata.season)
  if (metadata.category) formData.append('category', metadata.category)
  if (metadata.campus) formData.append('campus', metadata.campus)

  return request({
    url: '/api/v1/photos/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
    onUploadProgress: onProgress,
  })
}

export function updatePhoto(id: string, data: PhotoUpdate): Promise<Photo> {
  return request({ url: `/api/v1/photos/${id}`, method: 'patch', data })
}

export function deletePhoto(id: string): Promise<void> {
  return request({ url: `/api/v1/photos/${id}`, method: 'delete' })
}

export function updatePhotoTags(id: string, tagNames: string[]): Promise<Photo> {
  return request({ url: `/api/v1/photos/${id}/tags`, method: 'post', data: tagNames })
}

export function approvePhoto(id: string): Promise<Photo> {
  return request({ url: `/api/v1/photos/${id}/approve`, method: 'post' })
}

export function rejectPhoto(id: string): Promise<Photo> {
  return request({ url: `/api/v1/photos/${id}/reject`, method: 'post' })
}

export function batchApprovePhotos(photoIds: string[]): Promise<{ message: string; updated_count: number }> {
  return request({ url: '/api/v1/photos/batch-approve', method: 'post', data: photoIds })
}

export function batchRejectPhotos(photoIds: string[]): Promise<{ message: string; updated_count: number }> {
  return request({ url: '/api/v1/photos/batch-reject', method: 'post', data: photoIds })
}

export function batchDeletePhotos(photoIds: string[]): Promise<{ message: string; deleted_count: number }> {
  return request({ url: '/api/v1/photos/batch-delete', method: 'post', data: photoIds })
}

export function createPhotoAIAnalysis(photoId: string, force = false): Promise<AIAnalysisTask> {
  return request({
    url: `/api/v1/photos/${photoId}/ai-analysis`,
    method: 'post',
    data: { force },
  })
}

export function getPhotoAIAnalysis(photoId: string): Promise<AIAnalysisTask | null> {
  return request({
    url: `/api/v1/photos/${photoId}/ai-analysis`,
    method: 'get',
  })
}

export function applyPhotoAIAnalysis(photoId: string, taskId: string): Promise<AIApplyResponse> {
  return request({
    url: `/api/v1/photos/${photoId}/ai-analysis/${taskId}/apply`,
    method: 'post',
  })
}

export function ignorePhotoAIAnalysis(photoId: string, taskId: string): Promise<AIAnalysisTask> {
  return request({
    url: `/api/v1/photos/${photoId}/ai-analysis/${taskId}/ignore`,
    method: 'post',
  })
}
