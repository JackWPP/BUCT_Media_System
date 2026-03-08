/**
 * Photo state store.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Photo, PhotoFilters, PhotoListParams } from '../types/photo'
import * as photoApi from '../api/photo'

export const usePhotoStore = defineStore('photo', () => {
  const photos = ref<Photo[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const selectedPhoto = ref<Photo | null>(null)
  const filters = ref<PhotoFilters>({
    season: null,
    category: null,
    campus: null,
    building: null,
    gallery_series: null,
    gallery_year: null,
    photo_type: null,
    status: null,
    search: '',
    tag: null,
    sortBy: 'created_at',
    sortOrder: 'desc',
  })

  function buildQueryParams(params?: PhotoListParams) {
    const queryParams: Record<string, any> = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }

    if (filters.value.season) queryParams.season = filters.value.season
    if (filters.value.category) queryParams.category = filters.value.category
    if (filters.value.campus) queryParams.campus = filters.value.campus
    if (filters.value.building) queryParams.building = filters.value.building
    if (filters.value.gallery_series) queryParams.gallery_series = filters.value.gallery_series
    if (filters.value.gallery_year) queryParams.gallery_year = filters.value.gallery_year
    if (filters.value.photo_type) queryParams.photo_type = filters.value.photo_type
    if (filters.value.status) queryParams.status = filters.value.status
    if (filters.value.search) queryParams.search = filters.value.search
    if (filters.value.tag) queryParams.tag = filters.value.tag
    if (filters.value.sortBy) queryParams.sort_by = filters.value.sortBy
    if (filters.value.sortOrder) queryParams.sort_order = filters.value.sortOrder

    if (params) Object.assign(queryParams, params)
    return queryParams
  }

  async function fetchPhotos(params?: PhotoListParams) {
    loading.value = true
    try {
      const response = await photoApi.getPhotos(buildQueryParams(params))
      photos.value = response.items
      total.value = response.total
      return response
    } finally {
      loading.value = false
    }
  }

  async function fetchPublicPhotos(params?: PhotoListParams) {
    loading.value = true
    try {
      const response = await photoApi.getPublicPhotos(buildQueryParams(params))
      photos.value = response.items
      total.value = response.total
      return response
    } finally {
      loading.value = false
    }
  }

  async function fetchPublicPhotoDetail(id: string) {
    const photo = await photoApi.getPublicPhotoById(id)
    selectedPhoto.value = photo
    return photo
  }

  async function fetchPhotoDetail(id: string) {
    const photo = await photoApi.getPhotoById(id)
    selectedPhoto.value = photo
    return photo
  }

  async function updatePhoto(id: string, data: any) {
    const updatedPhoto = await photoApi.updatePhoto(id, data)
    const index = photos.value.findIndex((photo) => photo.id === id)
    if (index !== -1) photos.value[index] = updatedPhoto
    if (selectedPhoto.value?.id === id) selectedPhoto.value = updatedPhoto
    return updatedPhoto
  }

  async function deletePhoto(id: string) {
    await photoApi.deletePhoto(id)
    photos.value = photos.value.filter((photo) => photo.id !== id)
    total.value = Math.max(0, total.value - 1)
    if (selectedPhoto.value?.id === id) selectedPhoto.value = null
  }

  function setFilters(newFilters: Partial<PhotoFilters>) {
    filters.value = { ...filters.value, ...newFilters }
    currentPage.value = 1
  }

  function clearFilters() {
    filters.value = {
      season: null,
      category: null,
      campus: null,
      building: null,
      gallery_series: null,
      gallery_year: null,
      photo_type: null,
      status: null,
      search: '',
      tag: null,
      sortBy: 'created_at',
      sortOrder: 'desc',
    }
    currentPage.value = 1
  }

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
