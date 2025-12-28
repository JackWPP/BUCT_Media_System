/**
 * 照片状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Photo, PhotoFilters, PhotoListParams } from '../types/photo'
import * as photoApi from '../api/photo'

export const usePhotoStore = defineStore('photo', () => {
  // 状态
  const photos = ref<Photo[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const selectedPhoto = ref<Photo | null>(null)
  const filters = ref<PhotoFilters>({
    season: null,
    category: null,
    status: null,
    search: '',
    tag: null,
    sortBy: 'created_at',
    sortOrder: 'desc',
  })

  // 获取照片列表
  async function fetchPhotos(params?: PhotoListParams) {
    loading.value = true
    try {
      const queryParams: any = {
        skip: ((currentPage.value - 1) * pageSize.value),
        limit: pageSize.value,
      }

      // 只添加非 null 的筛选条件
      if (filters.value.season) queryParams.season = filters.value.season
      if (filters.value.category) queryParams.category = filters.value.category
      if (filters.value.status) queryParams.status = filters.value.status
      if (filters.value.search) queryParams.search = filters.value.search
      if (filters.value.tag) queryParams.tag = filters.value.tag

      // 添加额外参数
      if (params) {
        Object.assign(queryParams, params)
      }

      const response = await photoApi.getPhotos(queryParams)
      photos.value = response.items
      total.value = response.total

      return response
    } catch (error) {
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取公开照片列表（无需登录）
  async function fetchPublicPhotos(params?: PhotoListParams) {
    loading.value = true
    try {
      const queryParams: any = {
        skip: ((currentPage.value - 1) * pageSize.value),
        limit: pageSize.value,
      }

      // 只添加非 null 的筛选条件（不包括status，公开API固定返回approved）
      if (filters.value.season) queryParams.season = filters.value.season
      if (filters.value.category) queryParams.category = filters.value.category
      if (filters.value.search) queryParams.search = filters.value.search
      if (filters.value.tag) queryParams.tag = filters.value.tag
      if (filters.value.sortBy) queryParams.sort_by = filters.value.sortBy
      if (filters.value.sortOrder) queryParams.sort_order = filters.value.sortOrder

      // 添加额外参数
      if (params) {
        Object.assign(queryParams, params)
      }

      const response = await photoApi.getPublicPhotos(queryParams)
      photos.value = response.items
      total.value = response.total

      return response
    } catch (error) {
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取公开照片详情（无需登录）
  async function fetchPublicPhotoDetail(id: string) {
    try {
      const photo = await photoApi.getPublicPhotoById(id)
      selectedPhoto.value = photo
      return photo
    } catch (error) {
      throw error
    }
  }

  // 获取照片详情
  async function fetchPhotoDetail(id: string) {
    try {
      const photo = await photoApi.getPhotoById(id)
      selectedPhoto.value = photo
      return photo
    } catch (error) {
      throw error
    }
  }

  // 更新照片信息
  async function updatePhoto(id: string, data: any) {
    try {
      const updatedPhoto = await photoApi.updatePhoto(id, data)
      // 更新列表中的照片
      const index = photos.value.findIndex(p => p.id === id)
      if (index !== -1) {
        photos.value[index] = updatedPhoto
      }
      // 更新选中的照片
      if (selectedPhoto.value?.id === id) {
        selectedPhoto.value = updatedPhoto
      }
      return updatedPhoto
    } catch (error) {
      throw error
    }
  }

  // 删除照片
  async function deletePhoto(id: string) {
    try {
      await photoApi.deletePhoto(id)
      // 从列表中移除
      photos.value = photos.value.filter(p => p.id !== id)
      total.value -= 1
      // 清除选中
      if (selectedPhoto.value?.id === id) {
        selectedPhoto.value = null
      }
    } catch (error) {
      throw error
    }
  }

  // 设置筛选条件
  function setFilters(newFilters: Partial<PhotoFilters>) {
    filters.value = { ...filters.value, ...newFilters }
    currentPage.value = 1 // 重置页码
  }

  // 清除筛选条件
  function clearFilters() {
    filters.value = {
      season: null,
      category: null,
      status: null,
      search: '',
      tag: null,
      sortBy: 'created_at',
      sortOrder: 'desc',
    }
    currentPage.value = 1
  }

  // 设置当前页
  function setPage(page: number) {
    currentPage.value = page
  }

  return {
    photos,
    total,
    currentPage,
    pageSize,
    loading,
    selectedPhoto,
    filters,
    fetchPhotos,
    fetchPublicPhotos,
    fetchPhotoDetail,
    fetchPublicPhotoDetail,
    updatePhoto,
    deletePhoto,
    setFilters,
    clearFilters,
    setPage,
  }
})
