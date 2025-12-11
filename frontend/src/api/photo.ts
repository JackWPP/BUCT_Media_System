/**
 * 照片相关 API
 */
import request from './index'
import type {
  Photo,
  PhotoListParams,
  PhotoListResponse,
  PhotoUpdate,
  PhotoUploadResponse,
} from '../types/photo'

/**
 * 获取照片列表
 */
export function getPhotos(params?: PhotoListParams): Promise<PhotoListResponse> {
  return request({
    url: '/api/v1/photos',
    method: 'get',
    params,
  })
}

/**
 * 获取公开照片列表（无需登录，只返回已审核的照片）
 */
export function getPublicPhotos(params?: PhotoListParams): Promise<PhotoListResponse> {
  return request({
    url: '/api/v1/photos/public',
    method: 'get',
    params,
  })
}

/**
 * 获取照片详情
 */
export function getPhotoById(id: string): Promise<Photo> {
  return request({
    url: `/api/v1/photos/${id}`,
    method: 'get',
  })
}

/**
 * 获取公开照片详情（无需登录）
 */
export function getPublicPhotoById(id: string): Promise<Photo> {
  return request({
    url: `/api/v1/photos/public/${id}`,
    method: 'get',
  })
}

/**
 * 上传照片
 */
export function uploadPhoto(file: File, metadata?: {
  description?: string
  season?: string
  category?: string
}): Promise<PhotoUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  
  if (metadata?.description) {
    formData.append('description', metadata.description)
  }
  if (metadata?.season) {
    formData.append('season', metadata.season)
  }
  if (metadata?.category) {
    formData.append('category', metadata.category)
  }

  return request({
    url: '/api/v1/photos/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

/**
 * 更新照片信息
 */
export function updatePhoto(id: string, data: PhotoUpdate): Promise<Photo> {
  return request({
    url: `/api/v1/photos/${id}`,
    method: 'patch',
    data,
  })
}

/**
 * 删除照片
 */
export function deletePhoto(id: string): Promise<void> {
  return request({
    url: `/api/v1/photos/${id}`,
    method: 'delete',
  })
}

/**
 * 更新照片标签
 */
export function updatePhotoTags(id: string, tagIds: number[]): Promise<Photo> {
  return request({
    url: `/api/v1/photos/${id}/tags`,
    method: 'post',
    data: { tag_ids: tagIds },
  })
}

/**
 * 审批照片
 */
export function approvePhoto(id: string): Promise<Photo> {
  return request({
    url: `/api/v1/photos/${id}/approve`,
    method: 'post',
  })
}

/**
 * 拒绝照片
 */
export function rejectPhoto(id: string): Promise<Photo> {
  return request({
    url: `/api/v1/photos/${id}/reject`,
    method: 'post',
  })
}

/**
 * 批量审批照片
 */
export function batchApprovePhotos(photoIds: string[]): Promise<{ message: string; updated_count: number }> {
  return request({
    url: '/api/v1/photos/batch-approve',
    method: 'post',
    data: photoIds,
  })
}

/**
 * 批量拒绝照片
 */
export function batchRejectPhotos(photoIds: string[]): Promise<{ message: string; updated_count: number }> {
  return request({
    url: '/api/v1/photos/batch-reject',
    method: 'post',
    data: photoIds,
  })
}
