import request from './index'
import type { Photo } from '../types/photo'
import type { User } from '../types/user'

export interface TaggingTaskItem {
  id: string
  task_id: string
  photo_id: string
  status: string
  original_tags: string[] | null
  submitted_tags: string[] | null
  original_classifications: Record<string, any> | null
  submitted_classifications: Record<string, any> | null
  submitter_note: string | null
  reviewer_id: string | null
  reviewer_note: string | null
  submitted_at: string | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
  photo: Photo | null
}

export interface TaggingTask {
  id: string
  title: string
  description: string | null
  creator_id: string
  assignee_id: string
  status: string
  created_at: string
  updated_at: string
  completed_at: string | null
  items: TaggingTaskItem[]
}

export interface TaggingTaskListResponse {
  total: number
  items: TaggingTask[]
}

export interface TaggingTaskCreate {
  title: string
  description?: string
  assignee_id: string
  photo_ids: string[]
}

export interface TaggingTaskBatchCreate {
  title: string
  description?: string
  assignee_ids: string[]
  photo_ids?: string[]
  selection_mode: 'manual' | 'all' | 'zero_tags'
  status?: string | null
  search?: string
  photo_type?: '风光类' | '纪实类'
  max_photos?: number
}

export function getTaggingTasks(params?: { skip?: number; limit?: number }) {
  return request.get<TaggingTaskListResponse>('/api/v1/tagging-tasks', { params })
}

export function createTaggingTask(data: TaggingTaskCreate) {
  return request.post<TaggingTask>('/api/v1/tagging-tasks', data)
}

export function createTaggingTaskBatch(data: TaggingTaskBatchCreate) {
  return request.post<TaggingTask[]>('/api/v1/tagging-tasks/batch', data)
}

export function getTaggingAssignees() {
  return request.get<User[]>('/api/v1/tagging-tasks/assignees')
}

export function getTaggingPhotoCandidates(params?: {
  selection_mode?: 'all' | 'zero_tags'
  status?: string | null
  search?: string
  photo_type?: '风光类' | '纪实类'
  skip?: number
  limit?: number
}) {
  return request.get<{ total: number; items: Photo[] }>('/api/v1/tagging-tasks/photo-candidates', { params })
}

export function submitTaggingItem(itemId: string, data: {
  tags: string[]
  classifications: Record<string, number>
  note?: string
}) {
  return request.post<TaggingTaskItem>(`/api/v1/tagging-tasks/items/${itemId}/submit`, data)
}

export function approveTaggingItem(itemId: string, note?: string) {
  return request.post<TaggingTaskItem>(`/api/v1/tagging-tasks/items/${itemId}/approve`, { note })
}

export function rejectTaggingItem(itemId: string, note?: string) {
  return request.post<TaggingTaskItem>(`/api/v1/tagging-tasks/items/${itemId}/reject`, { note })
}
