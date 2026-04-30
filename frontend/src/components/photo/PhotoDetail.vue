<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    class="photo-detail-modal"
    style="width: 90%; max-width: 1200px;"
    title="照片详情"
    @after-leave="handleModalClose"
  >
    <n-spin :show="loading">
      <div v-if="photo" class="photo-detail">
        <n-grid :cols="2" :x-gap="24" :y-gap="24" responsive="screen">
          <n-grid-item>
            <div class="image-preview">
              <div v-if="hasPrev" class="nav-btn prev" @click="$emit('prev')">
                <n-icon size="30" color="white" :component="ChevronBackOutline" />
              </div>
              <div v-if="hasNext" class="nav-btn next" @click="$emit('next')">
                <n-icon size="30" color="white" :component="ChevronForwardOutline" />
              </div>

              <img
                v-if="photo"
                :key="photo.id"
                :src="getImageUrl(photo)"
                :alt="photo.filename"
                class="preview-image"
                @error="handleImageError"
              />

              <div class="image-actions">
                <n-button-group>
                  <n-button tertiary @click="downloadImage">
                    <template #icon>
                      <n-icon :component="DownloadOutline" />
                    </template>
                    下载
                  </n-button>
                  <n-button tertiary @click="shareImage">
                    <template #icon>
                      <n-icon :component="ShareSocialOutline" />
                    </template>
                    分享
                  </n-button>
                </n-button-group>
              </div>
            </div>
          </n-grid-item>

          <n-grid-item>
            <n-space vertical size="large">
              <n-descriptions :column="1" bordered size="small">
                <n-descriptions-item label="文件名">{{ photo.filename }}</n-descriptions-item>
                <n-descriptions-item label="尺寸">{{ photo.width }} x {{ photo.height }}</n-descriptions-item>
                <n-descriptions-item label="文件大小">{{ formatFileSize(photo.file_size) }}</n-descriptions-item>
                <n-descriptions-item label="上传时间">{{ formatDate(photo.created_at) }}</n-descriptions-item>
                <n-descriptions-item v-if="photo.captured_at" label="拍摄时间">{{ formatDate(photo.captured_at) }}</n-descriptions-item>
                <n-descriptions-item label="状态">
                  <n-tag :type="getStatusType(photo.status)">{{ getStatusText(photo.status) }}</n-tag>
                </n-descriptions-item>
              </n-descriptions>

              <n-form :model="formData">
                <n-form-item label="季节">
                  <n-select v-model:value="formData.season" :options="seasonOptions" clearable />
                </n-form-item>
                <n-form-item label="校区">
                  <n-select v-model:value="formData.campus" :options="campusOptions" clearable />
                </n-form-item>
                <n-form-item label="类别">
                  <n-select v-model:value="formData.category" :options="categoryOptions" clearable />
                </n-form-item>
                <n-form-item label="描述">
                  <n-input v-model:value="formData.description" type="textarea" :rows="3" placeholder="输入照片描述..." />
                </n-form-item>
              </n-form>

              <div>
                <n-text strong>自由标签</n-text>
                <n-space style="margin-top: 8px;" wrap>
                  <n-tag v-for="tag in photo.tags" :key="tag" closable @close="handleRemoveTag(tag)">
                    {{ tag }}
                  </n-tag>
                  <n-button size="small" @click="showAddTag = true">+ 添加标签</n-button>
                </n-space>
              </div>

              <div v-if="photo && adminMode">
                <n-text strong>受控分类</n-text>
                <n-space style="margin-top: 8px;" wrap>
                  <n-popover
                    v-for="classification in Object.values(photo.classifications || {})"
                    :key="classification.facet_key"
                    trigger="click"
                    placement="bottom"
                  >
                    <template #trigger>
                      <n-tag type="success" size="small" closable @close="(e) => handleRemoveClassification(classification.facet_key, e)">
                        {{ classification.facet_name }}: {{ classification.node_name }}
                      </n-tag>
                    </template>
                    <n-select
                      :value="classification.node_id"
                      :options="getFacetNodeOptions(classification.facet_key)"
                      style="width: 200px;"
                      @update:value="(val: number) => handleChangeClassification(classification.facet_key, val)"
                    />
                  </n-popover>
                  <n-button v-if="getUnclassifiedFacets().length" size="tiny" @click="showAddClassification = true">
                    + 添加分类
                  </n-button>
                </n-space>
                <!-- 添加分类弹出 -->
                <n-modal v-model:show="showAddClassification" preset="dialog" title="添加受控分类">
                  <n-form-item label="分类维度">
                    <n-select
                      v-model:value="addClassificationFacet"
                      :options="getUnclassifiedFacets()"
                      placeholder="选择分类维度"
                      style="width: 200px;"
                    />
                  </n-form-item>
                  <n-form-item v-if="addClassificationFacet" label="分类值">
                    <n-select
                      v-model:value="addClassificationNode"
                      :options="getFacetNodeOptions(addClassificationFacet)"
                      placeholder="选择分类值"
                      style="width: 200px;"
                    />
                  </n-form-item>
                  <template #action>
                    <n-button @click="showAddClassification = false">取消</n-button>
                    <n-button
                      type="primary"
                      :disabled="!addClassificationFacet || !addClassificationNode"
                      @click="handleAddClassification"
                    >
                      确定
                    </n-button>
                  </template>
                </n-modal>
              </div>
              <div v-else-if="photo && photo.classifications && Object.keys(photo.classifications).length">
                <n-text strong>受控分类</n-text>
                <n-space style="margin-top: 8px;" wrap>
                  <n-tag
                    v-for="classification in Object.values(photo.classifications)"
                    :key="classification.node_id"
                    type="success"
                    size="small"
                  >
                    {{ classification.facet_name }}: {{ classification.node_name }}
                  </n-tag>
                </n-space>
              </div>

              <div v-if="adminMode">
                <n-space justify="space-between" align="center">
                  <n-text strong>AI 建议</n-text>
                  <n-space>
                    <n-button size="small" :loading="aiLoading" @click="handleRunAI(false)">运行分析</n-button>
                    <n-button size="small" tertiary :loading="aiLoading" @click="handleRunAI(true)">强制重跑</n-button>
                  </n-space>
                </n-space>

                <n-spin :show="aiLoading">
                  <n-empty
                    v-if="!aiTask || !aiTask.result_json"
                    description="暂无 AI 建议"
                    size="small"
                    style="margin-top: 12px;"
                  />
                  <n-card v-else size="small" embedded style="margin-top: 12px;">
                    <n-space vertical size="small">
                      <n-space align="center">
                        <n-tag size="small" type="info">{{ aiTask.provider }}</n-tag>
                        <n-tag size="small" :type="aiTask.status === 'applied' ? 'success' : 'warning'">{{ aiTask.status }}</n-tag>
                        <n-text depth="3">置信度 {{ Math.round((aiTask.result_json.confidence || 0) * 100) }}%</n-text>
                      </n-space>

                      <n-text v-if="aiTask.result_json.summary">{{ aiTask.result_json.summary }}</n-text>

                      <div v-if="classificationSuggestions.length">
                        <n-text depth="3">候选分类</n-text>
                        <n-space style="margin-top: 8px;" wrap>
                          <n-tag v-for="item in classificationSuggestions" :key="item.key" size="small" type="success">
                            {{ item.label }}: {{ item.value }}
                          </n-tag>
                        </n-space>
                      </div>

                      <div v-if="aiTask.result_json.free_tags?.length">
                        <n-text depth="3">候选自由标签</n-text>
                        <n-space style="margin-top: 8px;" wrap>
                          <n-tag v-for="tag in aiTask.result_json.free_tags" :key="tag" size="small">{{ tag }}</n-tag>
                        </n-space>
                      </div>

                      <div v-if="aiTask.result_json.quality_flags?.length">
                        <n-text depth="3">质量提示</n-text>
                        <n-space style="margin-top: 8px;" wrap>
                          <n-tag v-for="flag in aiTask.result_json.quality_flags" :key="flag" size="small" type="warning">{{ flag }}</n-tag>
                        </n-space>
                      </div>

                      <div v-if="aiTask.result_json.risk_flags?.length">
                        <n-text depth="3">风险提示</n-text>
                        <n-space style="margin-top: 8px;" wrap>
                          <n-tag v-for="flag in aiTask.result_json.risk_flags" :key="flag" size="small" type="error">{{ flag }}</n-tag>
                        </n-space>
                      </div>

                      <n-alert v-if="Object.keys(unresolvedClassifications).length" type="warning" title="未命中受控词表">
                        {{ Object.entries(unresolvedClassifications).map(([key, value]) => `${key}: ${value}`).join('；') }}
                      </n-alert>

                      <n-space>
                        <n-button
                          size="small"
                          type="primary"
                          :disabled="aiTask.status !== 'completed'"
                          :loading="applyingAI"
                          @click="handleApplyAI"
                        >
                          应用建议
                        </n-button>
                        <n-button
                          size="small"
                          :disabled="aiTask.status !== 'completed'"
                          :loading="applyingAI"
                          @click="handleIgnoreAI"
                        >
                          忽略建议
                        </n-button>
                      </n-space>
                    </n-space>
                  </n-card>
                </n-spin>
              </div>

              <n-collapse v-if="photo.exif_data && Object.keys(photo.exif_data).length > 0">
                <n-collapse-item title="EXIF 数据" name="exif">
                  <n-descriptions :column="1" size="small">
                    <n-descriptions-item v-for="(value, key) in photo.exif_data" :key="key" :label="key">
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
        <n-popconfirm @positive-click="handleDelete">
          <template #trigger>
            <n-button type="error" :loading="deleting">删除照片</n-button>
          </template>
          确定要删除这张照片吗？此操作不可恢复。
        </n-popconfirm>

        <n-space>
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" :disabled="!hasChanges" @click="handleSave">保存修改</n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>

  <n-modal v-model:show="showAddTag" preset="dialog" title="添加标签">
    <n-input v-model:value="newTag" placeholder="输入标签名称" @keydown.enter="handleAddTag" />
    <template #action>
      <n-button @click="showAddTag = false">取消</n-button>
      <n-button type="primary" @click="handleAddTag">确定</n-button>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { ChevronBackOutline, ChevronForwardOutline, DownloadOutline, ShareSocialOutline } from '@vicons/ionicons5'
import dayjs from 'dayjs'
import { addPhotoTags, getPublicTags, removePhotoTag, type Tag } from '../../api/tag'
import {
  applyPhotoAIAnalysis,
  createPhotoAIAnalysis,
  getPhotoAIAnalysis,
  ignorePhotoAIAnalysis,
  updatePhotoClassifications,
  removePhotoClassification,
  type AIAnalysisTask,
} from '../../api/photo'
import { incrementView } from '../../api/stats'
import { SEASON_OPTIONS, CATEGORY_OPTIONS } from '../../constants/options'
import { usePhotoStore } from '../../stores/photo'
import type { Photo, PhotoUpdate } from '../../types/photo'
import { getPhotoUrl, getPhotoDownloadUrl } from '../../utils/format'
import { getPublicTaxonomy, type TaxonomyFacet } from '../../api/taxonomy'

interface Props {
  photoId?: string | null
  show?: boolean
  adminMode?: boolean
  hasPrev?: boolean
  hasNext?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  photoId: null,
  show: false,
  adminMode: false,
  hasPrev: false,
  hasNext: false,
})

const emit = defineEmits<{
  'update:show': [value: boolean]
  deleted: []
  updated: []
  prev: []
  next: []
}>()

const message = useMessage()
const photoStore = usePhotoStore()

const showModal = ref(props.show)
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const showAddTag = ref(false)
const newTag = ref('')
const photo = ref<Photo | null>(null)
const allTagsMap = ref<Map<string, number>>(new Map())
const aiTask = ref<AIAnalysisTask | null>(null)
const aiLoading = ref(false)
const applyingAI = ref(false)
const unresolvedClassifications = ref<Record<string, string>>({})

const formData = ref({
  season: null as string | null,
  category: null as string | null,
  campus: null as string | null,
  description: null as string | null,
})

const showAddClassification = ref(false)
const addClassificationFacet = ref<string | null>(null)
const addClassificationNode = ref<number | null>(null)

const seasonOptions = SEASON_OPTIONS
const categoryOptions = CATEGORY_OPTIONS
const taxonomyFacets = ref<TaxonomyFacet[]>([])

const campusOptions = computed(() => {
  const facet = taxonomyFacets.value.find((f) => f.key === 'campus')
  if (!facet) return []
  return facet.nodes.map((node) => ({ label: node.name, value: node.name }))
})

const hasChanges = computed(() => {
  if (!photo.value) return false
  return (
    formData.value.season !== photo.value.season ||
    formData.value.category !== photo.value.category ||
    formData.value.campus !== photo.value.campus ||
    formData.value.description !== photo.value.description
  )
})

const classificationSuggestions = computed(() => {
  const classifications = aiTask.value?.result_json?.classifications || {}
  const labelMap: Record<string, string> = {
    season: '季节',
    campus: '校区',
    building: '楼宇',
    gallery_series: '专题/赛事',
    gallery_year: '年份',
    photo_type: '照片类型',
  }
  return Object.entries(classifications)
    .filter(([, value]) => !!value)
    .map(([key, value]) => ({ key, label: labelMap[key] || key, value: String(value) }))
})

function handleKeydown(event: KeyboardEvent) {
  if (!props.show) return
  if (event.key === 'ArrowLeft' && props.hasPrev) emit('prev')
  if (event.key === 'ArrowRight' && props.hasNext) emit('next')
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch(
  () => props.show,
  (value) => {
    showModal.value = value
    if (value && props.photoId) {
      loadPhotoDetail()
    }
  },
)

watch(
  () => props.photoId,
  (newId, oldId) => {
    if (newId && newId !== oldId && props.show) {
      loadPhotoDetail()
    }
  },
)

watch(showModal, (value) => {
  emit('update:show', value)
})

function getImageUrl(currentPhoto: Photo) {
  return getPhotoUrl(currentPhoto.id, 'original')
}

function getThumbnailUrl(currentPhoto: Photo) {
  return getPhotoUrl(currentPhoto.id, 'thumbnail')
}

function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  if (!photo.value) return
  const thumbUrl = getThumbnailUrl(photo.value)
  if (img.getAttribute('data-tried-thumb') === 'true') {
    img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f0f0f0" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E图片加载失败%3C/text%3E%3C/svg%3E'
    return
  }
  img.setAttribute('data-tried-thumb', 'true')
  img.src = thumbUrl
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
  return dateString ? dayjs(dateString).format('YYYY-MM-DD HH:mm:ss') : '未知'
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
    approved: '已上线',
    pending: '待审核',
    rejected: '已拒绝',
  }
  return statusMap[status] || status
}

async function loadPhotoDetail() {
  if (!props.photoId) return
  loading.value = true
  try {
    const data = props.adminMode
      ? await photoStore.fetchPhotoDetail(props.photoId)
      : await photoStore.fetchPublicPhotoDetail(props.photoId)
    photo.value = data
    formData.value = {
      season: data.season,
      category: data.category,
      campus: data.campus,
      description: data.description,
    }
    incrementView(props.photoId).catch(() => {})
    await loadAllTags()
    await loadTaxonomy()
    if (props.adminMode) {
      await loadAITask()
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '加载照片详情失败')
  } finally {
    loading.value = false
  }
}

async function loadAllTags() {
  const response = (await getPublicTags({ limit: 1000 })) as unknown as { items: Tag[] }
  const tagMap = new Map<string, number>()
  response.items.forEach((tag) => {
    tagMap.set(tag.name, tag.id)
  })
  allTagsMap.value = tagMap
}

async function loadAITask() {
  if (!props.photoId || !props.adminMode) return
  aiLoading.value = true
  try {
    aiTask.value = await getPhotoAIAnalysis(props.photoId)
  } catch (error) {
    console.error(error)
  } finally {
    aiLoading.value = false
  }
}

async function handleRunAI(force: boolean) {
  if (!props.photoId) return
  aiLoading.value = true
  try {
    aiTask.value = await createPhotoAIAnalysis(props.photoId, force)
    unresolvedClassifications.value = {}
    message.success(force ? '已重新提交 AI 分析任务' : '已提交 AI 分析任务')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提交 AI 分析失败')
  } finally {
    aiLoading.value = false
  }
}

async function handleApplyAI() {
  if (!props.photoId || !aiTask.value) return
  applyingAI.value = true
  try {
    const response = await applyPhotoAIAnalysis(props.photoId, aiTask.value.id)
    aiTask.value = response.task
    unresolvedClassifications.value = response.unresolved_classifications || {}
    message.success('AI 建议已应用')
    emit('updated')
    await loadPhotoDetail()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '应用 AI 建议失败')
  } finally {
    applyingAI.value = false
  }
}

async function handleIgnoreAI() {
  if (!props.photoId || !aiTask.value) return
  applyingAI.value = true
  try {
    aiTask.value = await ignorePhotoAIAnalysis(props.photoId, aiTask.value.id)
    message.success('AI 建议已忽略')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '忽略 AI 建议失败')
  } finally {
    applyingAI.value = false
  }
}

async function loadTaxonomy() {
  try {
    taxonomyFacets.value = await getPublicTaxonomy()
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

async function handleSave() {
  if (!photo.value || !hasChanges.value) return
  saving.value = true
  try {
    const updateData: PhotoUpdate = {}
    if (formData.value.season !== photo.value.season) updateData.season = formData.value.season || undefined
    if (formData.value.category !== photo.value.category) updateData.category = formData.value.category || undefined
    if (formData.value.campus !== photo.value.campus) updateData.campus = formData.value.campus || undefined
    if (formData.value.description !== photo.value.description) updateData.description = formData.value.description || undefined
    await photoStore.updatePhoto(photo.value.id, updateData)
    message.success('保存成功')
    emit('updated')
    await loadPhotoDetail()
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
  const tagId = allTagsMap.value.get(tagName)
  if (!tagId) {
    message.error('标签不存在')
    return
  }
  try {
    const updatedPhoto = await removePhotoTag(photo.value.id, tagId)
    photo.value = updatedPhoto as Photo
    emit('updated')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '移除标签失败')
  }
}

async function handleAddTag() {
  if (!photo.value || !newTag.value.trim()) return
  try {
    const allTags = [...(photo.value.tags || []), newTag.value.trim()]
    const updatedPhoto = await addPhotoTags(photo.value.id, allTags)
    photo.value = updatedPhoto as Photo
    newTag.value = ''
    showAddTag.value = false
    emit('updated')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '添加标签失败')
  }
}

function getFacetNodeOptions(facetKey: string) {
  const facet = taxonomyFacets.value.find((f) => f.key === facetKey)
  if (!facet) return []
  const flatten = (nodes: TaxonomyFacet['nodes']): Array<{ label: string; value: number }> =>
    nodes.flatMap((node) => [
      { label: node.name, value: node.id },
      ...flatten(node.children || []),
    ])
  return flatten(facet.nodes)
}

function getUnclassifiedFacets() {
  if (!photo.value) return []
  const existingFacets = new Set(
    Object.keys(photo.value.classifications || {}),
  )
  return taxonomyFacets.value
    .filter((f) => f.is_active && !existingFacets.has(f.key))
    .map((f) => ({ label: f.name, value: f.key }))
}

async function handleChangeClassification(facetKey: string, nodeId: number) {
  if (!photo.value) return
  try {
    const updatedPhoto = await updatePhotoClassifications(photo.value.id, {
      [facetKey]: nodeId,
    })
    photo.value = updatedPhoto as Photo
    emit('updated')
    message.success('分类已更新')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '更新分类失败')
  }
}

async function handleRemoveClassification(facetKey: string, event: MouseEvent) {
  // n-tag's @close emits a MouseEvent, avoid triggering popover
  event.stopPropagation()
  if (!photo.value) return
  try {
    const updatedPhoto = await removePhotoClassification(photo.value.id, facetKey)
    photo.value = updatedPhoto as Photo
    emit('updated')
    message.success('分类已移除')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '移除分类失败')
  }
}

async function handleAddClassification() {
  if (!photo.value || !addClassificationFacet.value || !addClassificationNode.value) return
  try {
    const updatedPhoto = await updatePhotoClassifications(photo.value.id, {
      [addClassificationFacet.value]: addClassificationNode.value,
    })
    photo.value = updatedPhoto as Photo
    addClassificationFacet.value = null
    addClassificationNode.value = null
    showAddClassification.value = false
    emit('updated')
    message.success('分类已添加')
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '添加分类失败')
  }
}

function downloadImage() {
  if (!photo.value) return
  window.open(getPhotoDownloadUrl(photo.value.id), '_blank')
}

async function shareImage() {
  if (!photo.value) return
  const shareUrl = `${window.location.origin}/?photo=${photo.value.id}`
  try {
    await navigator.clipboard.writeText(shareUrl)
    message.success('分享链接已复制')
  } catch {
    message.error('复制分享链接失败')
  }
}

function handleModalClose() {
  photo.value = null
  aiTask.value = null
  unresolvedClassifications.value = {}
}
</script>

<style scoped>
.photo-detail {
  min-height: 480px;
}

.image-preview {
  position: relative;
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
  min-height: 420px;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  max-height: 720px;
  display: block;
}

.image-actions {
  position: absolute;
  right: 16px;
  bottom: 16px;
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  cursor: pointer;
  padding: 12px;
  background: rgba(15, 23, 42, 0.45);
  border-radius: 999px;
}

.nav-btn.prev {
  left: 16px;
}

.nav-btn.next {
  right: 16px;
}
</style>
