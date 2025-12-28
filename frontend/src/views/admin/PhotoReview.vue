<template>
  <div class="photo-review">
    <n-space vertical size="large">
      <!-- 标题和统计 -->
      <n-space justify="space-between" align="center">
        <n-text strong style="font-size: 24px;">照片审核</n-text>
        <n-space>
          <n-statistic label="待审核" :value="pendingCount" />
          <n-statistic label="已通过" :value="approvedCount" />
          <n-statistic label="已拒绝" :value="rejectedCount" />
        </n-space>
      </n-space>

      <!-- 筛选和操作 -->
      <n-space justify="space-between">
        <n-space>
          <n-radio-group v-model:value="statusFilter" @update:value="loadPhotos">
            <n-radio-button value="all">全部</n-radio-button>
            <n-radio-button value="pending">待审核</n-radio-button>
            <n-radio-button value="approved">已通过</n-radio-button>
            <n-radio-button value="rejected">已拒绝</n-radio-button>
          </n-radio-group>
        </n-space>
        
        <n-space>
          <n-input
            v-model:value="searchQuery"
            placeholder="搜索文件名..."
            clearable
            style="width: 200px;"
            @update:value="handleSearch"
          >
            <template #prefix>
              <n-icon :component="SearchOutline" />
            </template>
          </n-input>
          <n-button
            :disabled="selectedPhotos.length === 0"
            type="success"
            @click="handleBatchApprove"
          >
            通过({{ selectedPhotos.length }})
          </n-button>
          <n-button
            :disabled="selectedPhotos.length === 0"
            type="warning"
            @click="handleBatchReject"
          >
            拒绝({{ selectedPhotos.length }})
          </n-button>
          <n-popconfirm @positive-click="handleBatchDelete">
            <template #trigger>
              <n-button :disabled="selectedPhotos.length === 0" type="error">
                删除({{ selectedPhotos.length }})
              </n-button>
            </template>
            确定要永久删除这 {{ selectedPhotos.length }} 张照片吗？
          </n-popconfirm>
        </n-space>
      </n-space>

      <!-- 照片网格 -->
      <n-spin :show="loading">
        <div v-if="photos.length > 0" class="photos-grid">
          <div
            v-for="photo in photos"
            :key="photo.id"
            class="photo-card"
            :class="{ selected: selectedPhotos.includes(photo.id) }"
          >
            <div class="photo-checkbox">
              <n-checkbox
                :checked="selectedPhotos.includes(photo.id)"
                @update:checked="(checked: boolean) => toggleSelection(photo.id, checked)"
              />
            </div>
            <div class="photo-image" @click="viewPhotoDetail(photo)">
              <img :src="getImageUrl(photo)" :alt="photo.filename" />
              <div class="photo-overlay">
                <n-tag :type="getStatusType(photo.status)">
                  {{ getStatusText(photo.status) }}
                </n-tag>
              </div>
            </div>
            <div class="photo-info">
              <n-ellipsis style="max-width: 100%;">
                <n-text>{{ photo.filename }}</n-text>
              </n-ellipsis>
              <n-space size="small">
                <n-text depth="3" style="font-size: 12px;">
                  {{ photo.width }} × {{ photo.height }}
                </n-text>
              </n-space>
            </div>
            <div class="photo-actions">
              <n-button
                v-if="photo.status === 'pending'"
                size="small"
                type="success"
                @click="handleApprove(photo.id)"
              >
                通过
              </n-button>
              <n-button
                v-if="photo.status === 'pending'"
                size="small"
                type="error"
                @click="handleReject(photo.id)"
              >
                拒绝
              </n-button>
              <n-button
                v-if="photo.status === 'rejected'"
                size="small"
                type="success"
                @click="handleApprove(photo.id)"
              >
                重新通过
              </n-button>
              <n-button
                v-if="photo.status === 'approved'"
                size="small"
                type="error"
                @click="handleReject(photo.id)"
              >
                撤回
              </n-button>
            </div>
          </div>
        </div>
        <n-empty v-else description="没有照片" />
      </n-spin>

      <!-- 分页 -->
      <n-pagination
        v-model:page="currentPage"
        v-model:page-size="pageSize"
        :item-count="totalCount"
        show-size-picker
        :page-sizes="[20, 50, 100]"
        @update:page="loadPhotos"
        @update:page-size="handlePageSizeChange"
      />
    </n-space>

    <!-- 照片详情对话框 -->
    <PhotoDetail
      v-model:show="showDetail"
      :photo-id="selectedPhotoId"
      admin-mode
      @updated="loadPhotos"
      @deleted="loadPhotos"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { SearchOutline } from '@vicons/ionicons5'
import { getPhotos, approvePhoto, rejectPhoto, batchApprovePhotos, batchRejectPhotos, batchDeletePhotos } from '@/api/photo'
import PhotoDetail from '@/components/photo/PhotoDetail.vue'
import type { Photo } from '@/types/photo'

const message = useMessage()

const loading = ref(false)
const photos = ref<Photo[]>([])
const selectedPhotos = ref<string[]>([])
const statusFilter = ref('all')
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const totalPages = ref(0)

const showDetail = ref(false)
const selectedPhotoId = ref<string | null>(null)

// 统计数据
const pendingCount = ref(0)
const approvedCount = ref(0)
const rejectedCount = ref(0)

onMounted(() => {
  loadPhotos()
  loadStatistics()
})

async function loadPhotos() {
  loading.value = true
  try {
    const params: any = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }

    if (statusFilter.value !== 'all') {
      params.status = statusFilter.value
    }

    if (searchQuery.value) {
      params.search = searchQuery.value
    }

    const response = await getPhotos(params)
    photos.value = response.items
    totalCount.value = response.total
    totalPages.value = Math.ceil(response.total / pageSize.value)
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载照片失败')
  } finally {
    loading.value = false
  }
}

async function loadStatistics() {
  try {
    const [pending, approved, rejected] = await Promise.all([
      getPhotos({ status: 'pending', limit: 1 }),
      getPhotos({ status: 'approved', limit: 1 }),
      getPhotos({ status: 'rejected', limit: 1 }),
    ])
    
    pendingCount.value = pending.total
    approvedCount.value = approved.total
    rejectedCount.value = rejected.total
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

function handleSearch() {
  currentPage.value = 1
  loadPhotos()
}

function handlePageSizeChange() {
  currentPage.value = 1
  loadPhotos()
}

function toggleSelection(photoId: string, checked: boolean) {
  if (checked) {
    selectedPhotos.value.push(photoId)
  } else {
    const index = selectedPhotos.value.indexOf(photoId)
    if (index > -1) {
      selectedPhotos.value.splice(index, 1)
    }
  }
}

async function handleApprove(photoId: string) {
  try {
    await approvePhoto(photoId)
    message.success('照片已通过')
    loadPhotos()
    loadStatistics()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '操作失败')
  }
}

async function handleReject(photoId: string) {
  try {
    await rejectPhoto(photoId)
    message.success('照片已拒绝')
    loadPhotos()
    loadStatistics()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '操作失败')
  }
}

async function handleBatchApprove() {
  if (selectedPhotos.value.length === 0) return
  
  try {
    const result = await batchApprovePhotos(selectedPhotos.value)
    message.success(result.message)
    selectedPhotos.value = []
    loadPhotos()
    loadStatistics()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '批量操作失败')
  }
}

async function handleBatchReject() {
  if (selectedPhotos.value.length === 0) return
  
  try {
    const result = await batchRejectPhotos(selectedPhotos.value)
    message.success(result.message)
    selectedPhotos.value = []
    loadPhotos()
    loadStatistics()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '批量操作失败')
  }
}

async function handleBatchDelete() {
  if (selectedPhotos.value.length === 0) return
  
  try {
    const result = await batchDeletePhotos(selectedPhotos.value)
    message.success(result.message)
    selectedPhotos.value = []
    loadPhotos()
    loadStatistics()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '批量操作失败')
  }
}

function viewPhotoDetail(photo: Photo) {
  selectedPhotoId.value = photo.id
  showDetail.value = true
}

import { getPhotoUrl } from '../../utils/format'

function getImageUrl(photo: Photo) {
   return getPhotoUrl(photo.id, 'thumbnail')
}

function getStatusType(status: string): 'success' | 'warning' | 'error' | 'info' {
  const statusMap: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
    approved: 'success',
    pending: 'warning',
    rejected: 'error',
  }
  return statusMap[status] || 'info'
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    approved: '已通过',
    pending: '待审核',
    rejected: '已拒绝',
  }
  return statusMap[status] || status
}
</script>

<style scoped>
.photo-review {
  max-width: 1600px;
  margin: 0 auto;
}

.photos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.photo-card {
  position: relative;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  transition: all 0.3s;
}

.photo-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.photo-card.selected {
  border-color: #18a058;
}

.photo-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

.photo-image {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  cursor: pointer;
  background: #f5f5f5;
}

.photo-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.photo-image:hover img {
  transform: scale(1.05);
}

.photo-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}

.photo-info {
  padding: 12px;
}

.photo-actions {
  padding: 0 12px 12px;
  display: flex;
  gap: 8px;
}
</style>
