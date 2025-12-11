<template>
  <n-modal
    v-model:show="showModal"
    :mask-closable="true"
    preset="card"
    class="photo-detail-modal"
    style="width: 90%; max-width: 1200px;"
    title="照片详情"
    @after-leave="handleModalClose"
  >
    <n-spin :show="loading">
      <div v-if="photo" class="photo-detail">
        <n-grid :cols="2" :x-gap="24" :y-gap="24" responsive="screen">
          <!-- 左侧:图片展示 -->
          <n-grid-item>
            <div class="image-preview">
              <img
                :src="getImageUrl(photo)"
                :alt="photo.filename"
                class="preview-image"
                @error="handleImageError"
              />
              <div class="image-actions">
                <n-button-group>
                  <n-button @click="downloadImage" tertiary>
                    <template #icon>
                      <n-icon :component="DownloadOutline" />
                    </template>
                    下载
                  </n-button>
                  <n-button @click="shareImage" tertiary>
                    <template #icon>
                      <n-icon :component="ShareSocialOutline" />
                    </template>
                    分享
                  </n-button>
                </n-button-group>
              </div>
            </div>
          </n-grid-item>

          <!-- 右侧：详情信息 -->
          <n-grid-item>
            <n-space vertical size="large">
              <!-- 基本信息 -->
              <n-descriptions :column="1" bordered size="small">
                <n-descriptions-item label="文件名">
                  {{ photo.filename }}
                </n-descriptions-item>
                <n-descriptions-item label="尺寸">
                  {{ photo.width }} × {{ photo.height }}
                </n-descriptions-item>
                <n-descriptions-item label="文件大小">
                  {{ formatFileSize(photo.file_size) }}
                </n-descriptions-item>
                <n-descriptions-item label="上传时间">
                  {{ formatDate(photo.created_at) }}
                </n-descriptions-item>
                <n-descriptions-item v-if="photo.captured_at" label="拍摄时间">
                  {{ formatDate(photo.captured_at) }}
                </n-descriptions-item>
                <n-descriptions-item label="状态">
                  <n-tag :type="getStatusType(photo.status)">
                    {{ getStatusText(photo.status) }}
                  </n-tag>
                </n-descriptions-item>
              </n-descriptions>

              <!-- 可编辑信息 -->
              <n-form ref="formRef" :model="formData">
                <n-form-item label="季节">
                  <n-select
                    v-model:value="formData.season"
                    :options="seasonOptions"
                    clearable
                  />
                </n-form-item>
                <n-form-item label="类别">
                  <n-select
                    v-model:value="formData.category"
                    :options="categoryOptions"
                    clearable
                  />
                </n-form-item>
                <n-form-item label="描述">
                  <n-input
                    v-model:value="formData.description"
                    type="textarea"
                    placeholder="输入照片描述..."
                    :rows="3"
                  />
                </n-form-item>
              </n-form>

              <!-- 标签 -->
              <div>
                <n-text strong>标签</n-text>
                <n-space style="margin-top: 8px;">
                  <n-tag
                    v-for="tag in photo.tags"
                    :key="tag"
                    closable
                    @close="handleRemoveTag(tag)"
                  >
                    {{ tag }}
                  </n-tag>
                  <n-button size="small" @click="showAddTag = true">
                    + 添加标签
                  </n-button>
                </n-space>
              </div>

              <!-- EXIF 信息 -->
              <n-collapse v-if="photo.exif_data && Object.keys(photo.exif_data).length > 0">
                <n-collapse-item title="EXIF 数据" name="exif">
                  <n-descriptions :column="1" size="small">
                    <n-descriptions-item
                      v-for="(value, key) in photo.exif_data"
                      :key="key"
                      :label="key"
                    >
                      {{ value }}
                    </n-descriptions-item>
                  </n-descriptions>
                </n-collapse-item>
              </n-collapse>
            </n-space>
          </n-grid-item>
        </n-grid>
      </div>
    </n-spin>

    <template #footer>
      <n-space justify="space-between">
        <n-popconfirm
          @positive-click="handleDelete"
        >
          <template #trigger>
            <n-button type="error" :loading="deleting">
              删除照片
            </n-button>
          </template>
          确定要删除这张照片吗？此操作不可恢复。
        </n-popconfirm>
        <n-space>
          <n-button @click="showModal = false">
            取消
          </n-button>
          <n-button
            type="primary"
            :loading="saving"
            :disabled="!hasChanges"
            @click="handleSave"
          >
            保存修改
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>

  <!-- 添加标签对话框 -->
  <n-modal v-model:show="showAddTag" preset="dialog" title="添加标签">
    <n-input
      v-model:value="newTag"
      placeholder="输入标签名称"
      @keydown.enter="handleAddTag"
    />
    <template #action>
      <n-button @click="showAddTag = false">取消</n-button>
      <n-button type="primary" @click="handleAddTag">确定</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { DownloadOutline, ShareSocialOutline } from '@vicons/ionicons5'
import type { Photo, PhotoUpdate } from '../../types/photo'
import { usePhotoStore } from '../../stores/photo'
import { getPopularTags, getPublicTags, addPhotoTags, removePhotoTag, type Tag } from '../../api/tag'
import dayjs from 'dayjs'

interface Props {
  photoId?: string | null
  show?: boolean
  adminMode?: boolean  // 是否在管理后台使用（使用已认证 API）
}

const props = withDefaults(defineProps<Props>(), {
  photoId: null,
  show: false,
  adminMode: false,
})

const emit = defineEmits<{
  'update:show': [value: boolean]
  'deleted': []
  'updated': []
}>()

const message = useMessage()
const photoStore = usePhotoStore()

const showModal = ref(props.show)
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const photo = ref<Photo | null>(null)
const showAddTag = ref(false)
const newTag = ref('')
const popularTags = ref<Tag[]>([])
const loadingTags = ref(false)
const allTagsMap = ref<Map<string, number>>(new Map())

const formData = ref({
  season: null as string | null,
  category: null as string | null,
  description: null as string | null,
})

const seasonOptions = [
  { label: 'Spring', value: 'Spring' },
  { label: 'Summer', value: 'Summer' },
  { label: 'Autumn', value: 'Autumn' },
  { label: 'Winter', value: 'Winter' },
]

const categoryOptions = [
  { label: 'Landscape', value: 'Landscape' },
  { label: 'Portrait', value: 'Portrait' },
  { label: 'Activity', value: 'Activity' },
  { label: 'Documentary', value: 'Documentary' },
]

const hasChanges = computed(() => {
  if (!photo.value) return false
  return (
    formData.value.season !== photo.value.season ||
    formData.value.category !== photo.value.category ||
    formData.value.description !== photo.value.description
  )
})

watch(() => props.show, (val) => {
  showModal.value = val
  if (val && props.photoId) {
    loadPhotoDetail()
  }
})

watch(showModal, (val) => {
  emit('update:show', val)
})

function getImageUrl(photo: Photo) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  let path = (photo.original_path || '').replace(/\\/g, '/')
  
  // 尝试从路径中提取 'uploads/' 开始的部分
  // 这可以处理后端存储了绝对路径的情况 (例如 D:/backend/uploads/...)
  const uploadsIndex = path.indexOf('uploads/')
  if (uploadsIndex !== -1) {
    path = path.substring(uploadsIndex)
  }
  
  // 确保没有前导 /
  if (path.startsWith('/')) path = path.substring(1)
  
  return path ? `${baseUrl}/${path}` : ''
}

function getThumbnailUrl(photo: Photo) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  let path = (photo.thumb_path || '').replace(/\\/g, '/')
  
  const uploadsIndex = path.indexOf('uploads/')
  if (uploadsIndex !== -1) {
    path = path.substring(uploadsIndex)
  }
  
  if (path.startsWith('/')) path = path.substring(1)
  return path ? `${baseUrl}/${path}` : ''
}

function handleImageError(e: Event) {
  const img = e.target as HTMLImageElement
  if (!photo.value) return

  const thumbUrl = getThumbnailUrl(photo.value)
  // 如果当前显示的不是缩略图，且缩略图存在，尝试降级
  if (thumbUrl && !img.src.includes('data:image')) {
     if (img.getAttribute('data-tried-thumb') === 'true') {
        img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
     } else {
        img.setAttribute('data-tried-thumb', 'true')
        img.src = thumbUrl
     }
  } else {
    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
  }
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '未知'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '未知'
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

function getStatusType(status: string): 'success' | 'warning' | 'error' | 'info' {
  const statusMap: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
    approved: 'success',
    pending: 'warning',
    rejected: 'error',
    active: 'success',
  }
  return statusMap[status] || 'info'
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    approved: '已上线',
    pending: '待审核',
    rejected: '已拒绝',
    active: '正常',
  }
  return statusMap[status] || status
}

async function loadPhotoDetail() {
  if (!props.photoId) return
  
  loading.value = true
  try {
    // 根据模式选择 API：管理后台使用已认证 API，前台使用公开 API
    const data = props.adminMode
      ? await photoStore.fetchPhotoDetail(props.photoId)
      : await photoStore.fetchPublicPhotoDetail(props.photoId)
    photo.value = data
    formData.value = {
      season: data.season,
      category: data.category,
      description: data.description,
    }
    
    // 加载所有标签（用于删除时获取 ID）
    await loadAllTags()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载照片详情失败')
  } finally {
    loading.value = false
  }
}

async function loadAllTags() {
  try {
    // 使用公开API获取标签列表
    const response = await getPublicTags({ limit: 1000 }) as unknown as { items: Tag[], total: number }
    const tagMap = new Map<string, number>()
    
    response.items.forEach((tag: Tag) => {
      tagMap.set(tag.name, tag.id)
    })
    
    allTagsMap.value = tagMap
  } catch (error) {
    console.error('加载标签失败:', error)
  }
}

async function loadPopularTags() {
  loadingTags.value = true
  try {
    popularTags.value = await getPopularTags(20) as unknown as Tag[]
  } catch (error) {
    console.error('加载热门标签失败:', error)
  } finally {
    loadingTags.value = false
  }
}

async function handleSave() {
  if (!photo.value || !hasChanges.value) return

  saving.value = true
  try {
    const updateData: PhotoUpdate = {}
    if (formData.value.season !== photo.value.season) {
      updateData.season = formData.value.season || undefined
    }
    if (formData.value.category !== photo.value.category) {
      updateData.category = formData.value.category || undefined
    }
    if (formData.value.description !== photo.value.description) {
      updateData.description = formData.value.description || undefined
    }

    await photoStore.updatePhoto(photo.value.id, updateData)
    message.success('保存成功')
    emit('updated')
    await loadPhotoDetail() // 重新加载
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!photo.value) return

  deleting.value = true
  try {
    await photoStore.deletePhoto(photo.value.id)
    message.success('删除成功')
    emit('deleted')
    showModal.value = false
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '删除失败')
  } finally {
    deleting.value = false
  }
}

async function handleRemoveTag(tagName: string) {
  if (!photo.value) return
  
  // 找到对应的标签 ID
  const tagId = allTagsMap.value.get(tagName)
  if (!tagId) {
    message.error('标签不存在')
    return
  }
  
  try {
    await removePhotoTag(photo.value.id, tagId)
    message.success('标签已删除')
    await loadPhotoDetail() // 重新加载照片详情
    emit('updated')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '删除标签失败')
  }
}

async function handleAddTag() {
  if (!newTag.value.trim()) {
    message.warning('请输入标签名称')
    return
  }
  
  if (!photo.value) return
  
  try {
    // 合并现有标签和新标签
    const newTagName = newTag.value.trim().toLowerCase()
    const allTags = [...(photo.value.tags || []), newTagName]
    
    // 调用 API 添加标签（需要传递所有标签）
    await addPhotoTags(photo.value.id, allTags)
    message.success('标签已添加')
    newTag.value = ''
    showAddTag.value = false
    await loadPhotoDetail() // 重新加载照片详情
    emit('updated')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '添加标签失败')
  }
}

function handleModalClose() {
  photo.value = null
  formData.value = {
    season: null,
    category: null,
    description: null,
  }
}

async function downloadImage() {
  if (!photo.value) return
  
  try {
    // 使用下载API端点（支持CORS）
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    // original_path 格式为 /uploads/originals/xxx.jpg
    // 转换为 /api/v1/download/originals/xxx.jpg
    const pathParts = photo.value.original_path?.replace('/uploads/', '').split('/') || []
    if (pathParts.length < 2) {
      message.error('无效的文件路径')
      return
    }
    const folder = pathParts[0]
    const filename = pathParts.slice(1).join('/')
    const downloadUrl = `${baseUrl}/api/v1/download/${folder}/${filename}`
    
    const response = await fetch(downloadUrl)
    if (!response.ok) {
      throw new Error('Download failed')
    }
    const blob = await response.blob()
    
    // 创建下载链接
    const blobUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = photo.value.filename
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(blobUrl)
    
    message.success('下载开始')
  } catch (error) {
    console.error('下载失败:', error)
    message.error('下载失败')
  }
}

function shareImage() {
  if (!photo.value) return
  const url = getImageUrl(photo.value)
  if (navigator.share) {
    navigator.share({
      title: photo.value.filename,
      text: photo.value.description || '',
      url: url
    }).catch(() => {
      copyToClipboard(url)
    })
  } else {
    copyToClipboard(url)
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    message.success('链接已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}
</script>

<style scoped>
.photo-detail {
  min-height: 400px;
}

.image-preview {
  position: sticky;
  top: 20px;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
}

.preview-image {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
}

.image-actions {
  padding: 12px;
  background: linear-gradient(to top, rgba(255,255,255,0.95), rgba(255,255,255,0.85));
  display: flex;
  justify-content: center;
  border-top: 1px solid #eee;
}

.photo-detail-modal :deep(.n-card__content) {
  padding: 24px;
}

@media (max-width: 768px) {
  .photo-detail :deep(.n-grid) {
    grid-template-columns: 1fr !important;
  }
  
  .image-preview {
    position: relative;
    top: 0;
  }
}
</style>
