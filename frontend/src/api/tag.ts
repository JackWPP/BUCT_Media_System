import request from './index'

/**
 * 标签相关 API
 */

/** 标签响应类型 */
export interface Tag {
  id: number
  name: string
  category?: string
  color?: string
  usage_count: number
  created_at: string
}

/** 标签列表响应 */
export interface TagListResponse {
  total: number
  items: Tag[]
}

/** 创建标签 */
export interface TagCreate {
  name: string
  category?: string
  color?: string
}

/** 更新标签 */
export interface TagUpdate {
  name?: string
  category?: string
  color?: string
}

/**
 * 获取标签列表
 */
export function getTags(params?: {
  skip?: number
  limit?: number
  search?: string
  category?: string
}) {
  return request.get<TagListResponse>('/api/v1/tags', { params })
}

/**
 * 获取公开标签列表（无需登录）
 */
export function getPublicTags(params?: {
  skip?: number
  limit?: number
  search?: string
  category?: string
}) {
  return request.get<TagListResponse>('/api/v1/tags/public', { params })
}

/**
 * 获取热门标签
 */
export function getPopularTags(limit = 20) {
  return request.get<Tag[]>('/api/v1/tags/popular', { params: { limit } })
}

/**
 * 创建标签（仅管理员）
 */
export function createTag(data: TagCreate) {
  return request.post<Tag>('/api/v1/tags', data)
}

/**
 * 获取标签详情
 */
export function getTag(tagId: number) {
  return request.get<Tag>(`/api/v1/tags/${tagId}`)
}

/**
 * 更新标签（仅管理员）
 */
export function updateTag(tagId: number, data: TagUpdate) {
  return request.patch<Tag>(`/api/v1/tags/${tagId}`, data)
}

/**
 * 删除标签（仅管理员）
 */
export function deleteTag(tagId: number) {
  return request.delete(`/api/v1/tags/${tagId}`)
}

/**
 * 为照片添加标签
 */
export function addPhotoTags(photoId: string, tagNames: string[]) {
  return request.post(`/api/v1/photos/${photoId}/tags`, tagNames)
}

/**
 * 从照片移除标签
 */
export function removePhotoTag(photoId: string, tagId: number) {
  return request.delete(`/api/v1/photos/${photoId}/tags/${tagId}`)
}
