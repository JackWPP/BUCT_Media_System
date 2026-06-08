<template>
  <div class="tagging-admin">
    <n-space vertical size="large">
      <n-space justify="space-between" align="center">
        <n-text strong style="font-size: 24px">标注任务</n-text>
        <n-space>
          <n-button @click="loadData" :loading="loading">刷新</n-button>
          <n-button type="primary" @click="openCreate">新建任务</n-button>
        </n-space>
      </n-space>

      <n-card v-for="task in tasks" :key="task.id" size="small">
        <template #header>
          <div class="task-header">
            <div>
              <strong>{{ task.title }}</strong>
              <p>{{ task.description || '完整标签体系任务：来源、校区、题材和明显可见细分标签' }}</p>
            </div>
            <n-space>
              <n-tag>{{ assigneeLabel(task.assignee_id) }}</n-tag>
              <n-tag>{{ statusLabel(task.status) }}</n-tag>
            </n-space>
          </div>
        </template>

        <div class="stats-row">
          <div v-for="metric in taskMetrics(task)" :key="metric.label" class="stat-cell">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.value }}</strong>
          </div>
          <div class="stat-progress">
            <span>完成率</span>
            <n-progress type="line" :percentage="task.stats?.completion_rate || 0" :height="8" />
          </div>
        </div>

        <n-space justify="space-between" align="center" class="table-toolbar">
          <n-text depth="3">只会批量处理待审核条目；已通过或已驳回不会被重审。</n-text>
          <n-space>
            <n-button
              size="small"
              type="primary"
              :disabled="!selectedSubmittedIds(task).length"
              :loading="reviewing"
              @click="batchReview(task, true)"
            >
              批量通过
            </n-button>
            <n-button
              size="small"
              type="error"
              :disabled="!selectedSubmittedIds(task).length"
              :loading="reviewing"
              @click="batchReview(task, false)"
            >
              批量驳回
            </n-button>
          </n-space>
        </n-space>

        <n-data-table
          v-model:checked-row-keys="checkedRowsByTask[task.id]"
          :columns="columns"
          :data="task.items"
          :bordered="false"
          :row-key="(row) => row.id"
          size="small"
        />
      </n-card>
      <n-empty v-if="!tasks.length && !loading" description="暂无标注任务" />
    </n-space>

    <n-modal v-model:show="showDetail" preset="card" title="审核差异详情" class="detail-modal">
      <div v-if="detailItem?.photo" class="detail-layout">
        <div class="detail-image">
          <img :src="getPhotoUrl(detailItem.photo.id, 'compressed')" :alt="detailItem.photo.filename" />
        </div>
        <div class="diff-panel">
          <n-space vertical size="large">
            <div>
              <n-text strong>{{ detailItem.photo.filename }}</n-text>
              <p>{{ detailItem.photo.description || '暂无描述' }}</p>
            </div>
            <n-data-table :columns="diffColumns" :data="diffRows" size="small" :bordered="false" />
            <n-input v-model:value="reviewNote" type="textarea" :rows="3" placeholder="审核意见（可选）" />
            <n-space justify="end">
              <n-button type="error" :disabled="detailItem.status !== 'submitted'" @click="review(detailItem, false, reviewNote)">驳回</n-button>
              <n-button type="primary" :disabled="detailItem.status !== 'submitted'" @click="review(detailItem, true, reviewNote)">通过</n-button>
            </n-space>
          </n-space>
        </div>
      </div>
    </n-modal>

    <n-modal v-model:show="showCreate" preset="card" title="批量新建标注任务" class="create-modal">
      <n-space vertical size="large">
        <n-alert type="info" :show-icon="false">
          新任务默认覆盖完整标签体系，标注同学主要确认来源、校区、题材，并补充明显可见的内容标签。
        </n-alert>
        <n-form :model="form" label-placement="left" label-width="90">
          <n-form-item label="任务名称">
            <n-input v-model:value="form.title" placeholder="例如：五月图库标签补充" />
          </n-form-item>
          <n-form-item label="说明">
            <n-input v-model:value="form.description" type="textarea" :rows="2" />
          </n-form-item>
          <n-form-item label="标注学生">
            <n-select
              v-model:value="form.assignee_ids"
              multiple
              :options="taggerOptions"
              filterable
              placeholder="选择一个或多个 tagger 账号"
            />
          </n-form-item>
        </n-form>

        <n-card size="small" title="候选照片">
          <template #header-extra>
            <n-space align="center">
              <n-radio-group v-model:value="candidateMode" size="small" @update:value="reloadCandidates">
                <n-radio-button value="all">全部照片</n-radio-button>
                <n-radio-button value="zero_tags">0 标签照片</n-radio-button>
              </n-radio-group>
              <n-radio-group v-model:value="candidatePhotoType" size="small" @update:value="reloadCandidates">
                <n-radio-button value="">全部题材</n-radio-button>
                <n-radio-button value="建筑楼宇">建筑楼宇</n-radio-button>
                <n-radio-button value="校区设施">校区设施</n-radio-button>
                <n-radio-button value="自然生态">自然生态</n-radio-button>
              </n-radio-group>
              <n-input
                v-model:value="candidateSearch"
                placeholder="搜索文件名/描述/标签"
                clearable
                style="width: 220px"
                @keyup.enter="reloadCandidates"
              />
              <n-button size="small" @click="reloadCandidates">筛选</n-button>
            </n-space>
          </template>

          <n-space justify="space-between" align="center" class="candidate-toolbar">
            <n-space>
              <n-button size="small" @click="selectCurrentPage">选中当前页</n-button>
              <n-button size="small" @click="clearSelection">清空选择</n-button>
              <n-checkbox v-model:checked="assignAllMatched">
                分派全部匹配照片（{{ candidateTotal }} 张）
              </n-checkbox>
            </n-space>
            <n-text depth="3">已手动选择 {{ selectedPhotoIds.length }} 张</n-text>
          </n-space>

          <n-spin :show="candidateLoading">
            <div class="photo-grid">
              <div
                v-for="photo in candidates"
                :key="photo.id"
                class="photo-tile"
                :class="{ selected: selectedSet.has(photo.id) }"
                @click="togglePhoto(photo.id)"
              >
                <img :src="getPhotoUrl(photo.id, 'thumbnail')" :alt="photo.filename" />
                <div class="tile-check">
                  <n-checkbox :checked="selectedSet.has(photo.id)" @click.stop @update:checked="() => togglePhoto(photo.id)" />
                </div>
                <div class="tile-meta">
                  <span>{{ photo.filename }}</span>
                  <n-tag size="tiny">{{ (photo.free_tags || photo.tags || []).length }} 标签</n-tag>
                </div>
              </div>
            </div>
          </n-spin>

          <n-pagination
            v-model:page="candidatePage"
            :page-size="candidatePageSize"
            :item-count="candidateTotal"
            style="margin-top: 12px"
            @update:page="loadCandidates"
          />
        </n-card>
      </n-space>

      <template #footer>
        <n-space justify="space-between" align="center">
          <n-text depth="3">
            将按学生数平均分派，生成 {{ form.assignee_ids.length || 0 }} 个任务。
          </n-text>
          <n-space>
            <n-button @click="showCreate = false">取消</n-button>
            <n-button type="primary" :loading="submitting" @click="createBatchTasks">创建并平均分派</n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NImage, NSpace, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import {
  approveTaggingItem,
  batchApproveTaggingItems,
  batchRejectTaggingItems,
  createTaggingTaskBatch,
  getTaggingAssignees,
  getTaggingPhotoCandidates,
  getTaggingTasks,
  rejectTaggingItem,
  type TaggingTask,
  type TaggingTaskItem,
} from '@/api/taggingTasks'
import type { Photo } from '@/types/photo'
import type { User } from '@/types/user'
import { getPhotoUrl } from '@/utils/format'
import { getPublicTaxonomy, type TaxonomyFacet } from '@/api/taxonomy'
import { FACET_LABELS, facetLabel, findTaxonomyNode } from '@/utils/taxonomy'

type DiffRow = { field: string; original: string; submitted: string; changed: boolean }

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const reviewing = ref(false)
const showCreate = ref(false)
const showDetail = ref(false)
const tasks = ref<TaggingTask[]>([])
const users = ref<User[]>([])
const taxonomyFacets = ref<TaxonomyFacet[]>([])
const candidates = ref<Photo[]>([])
const candidateLoading = ref(false)
const candidateTotal = ref(0)
const candidatePage = ref(1)
const candidatePageSize = 36
const candidateMode = ref<'all' | 'zero_tags'>('zero_tags')
const candidatePhotoType = ref<'' | '建筑楼宇' | '校区设施' | '自然生态'>('')
const candidateSearch = ref('')
const selectedPhotoIds = ref<string[]>([])
const assignAllMatched = ref(true)
const checkedRowsByTask = reactive<Record<string, string[]>>({})
const detailItem = ref<TaggingTaskItem | null>(null)
const reviewNote = ref('')

const form = reactive({
  title: '',
  description: '',
  assignee_ids: [] as string[],
})

const selectedSet = computed(() => new Set(selectedPhotoIds.value))

const taggerOptions = computed(() =>
  users.value
    .filter((user) => ['tagger', 'auditor', 'admin'].includes(user.role))
    .map((user) => ({
      label: `${user.full_name || user.student_id || user.email} (${user.role})`,
      value: user.id,
    })),
)

const columns: DataTableColumns<TaggingTaskItem> = [
  {
    type: 'selection',
    disabled(row) {
      return row.status !== 'submitted'
    },
  },
  {
    title: '照片',
    key: 'photo',
    width: 260,
    render(row) {
      return h(NSpace, { align: 'center' }, {
        default: () => [
          row.photo ? h(NImage, { src: getPhotoUrl(row.photo.id, 'thumbnail'), width: 64, height: 42, objectFit: 'cover' }) : null,
          h('span', { class: 'filename-cell' }, row.photo?.filename || row.photo_id),
        ],
      })
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 110,
    render(row) {
      return h(NTag, { size: 'small', type: statusType(row.status) }, { default: () => statusLabel(row.status) })
    },
  },
  {
    title: '提交内容',
    key: 'submitted',
    render(row) {
      const tags = (row.submitted_tags || []).join('、')
      const classifications = classificationSummary(row.submitted_classifications)
      return tags || classifications || '-'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render(row) {
      return h(NSpace, {}, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openDetail(row) }, { default: () => '详情' }),
          h(NButton, { size: 'small', type: 'primary', disabled: row.status !== 'submitted', onClick: () => review(row, true) }, { default: () => '通过' }),
          h(NButton, { size: 'small', type: 'error', disabled: row.status !== 'submitted', onClick: () => review(row, false) }, { default: () => '驳回' }),
        ],
      })
    },
  },
]

const diffColumns: DataTableColumns<DiffRow> = [
  { title: '字段', key: 'field', width: 100 },
  { title: '原值', key: 'original' },
  {
    title: '提交值',
    key: 'submitted',
    render(row) {
      return h('span', { class: row.changed ? 'changed-value' : '' }, row.submitted || '-')
    },
  },
]

const diffRows = computed<DiffRow[]>(() => {
  const item = detailItem.value
  if (!item) return []
  const fields = new Set<string>([
    ...Object.keys(item.original_classifications || item.photo?.classifications || {}),
    ...Object.keys(item.submitted_classifications || {}),
  ])
  const rows = [...fields].map((field) => {
    const original = classificationValue(field, item.original_classifications?.[field] || item.photo?.classifications?.[field])
    const submitted = classificationValue(field, item.submitted_classifications?.[field])
    return { field: facetLabel(field, taxonomyFacets.value), original, submitted, changed: original !== submitted }
  })
  const originalTagList = item.original_tags || item.photo?.free_tags || item.photo?.tags || []
  const submittedTagList = item.submitted_tags || []
  rows.unshift({
    field: FACET_LABELS.tag,
    original: originalTagList.join('、'),
    submitted: tagDiffSummary(originalTagList, submittedTagList),
    changed: sortedText(originalTagList) !== sortedText(submittedTagList),
  })
  return rows
})

onMounted(loadData)

async function loadData() {
  loading.value = true
  try {
    const [taskResponse, userResponse, facets] = await Promise.all([
      getTaggingTasks({ limit: 100 }),
      getTaggingAssignees(),
      getPublicTaxonomy(),
    ])
    tasks.value = taskResponse.items
    users.value = userResponse
    taxonomyFacets.value = facets
    tasks.value.forEach((task) => {
      checkedRowsByTask[task.id] = checkedRowsByTask[task.id] || []
    })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  showCreate.value = true
  if (!candidates.value.length) loadCandidates()
}

function openDetail(row: TaggingTaskItem) {
  detailItem.value = row
  reviewNote.value = row.reviewer_note || ''
  showDetail.value = true
}

function assigneeLabel(id: string) {
  const user = users.value.find((item) => item.id === id)
  return user?.full_name || user?.student_id || user?.email || id
}

function taskMetrics(task: TaggingTask) {
  const stats = task.stats || { total: task.items.length, pending: 0, submitted: 0, approved: 0, rejected: 0 }
  return [
    { label: '总数', value: stats.total },
    { label: '待标注', value: stats.pending },
    { label: '待审核', value: stats.submitted },
    { label: '已通过', value: stats.approved },
    { label: '已驳回', value: stats.rejected },
  ]
}

function selectedSubmittedIds(task: TaggingTask) {
  const ids = new Set(checkedRowsByTask[task.id] || [])
  return task.items.filter((item) => ids.has(item.id) && item.status === 'submitted').map((item) => item.id)
}

async function reloadCandidates() {
  candidatePage.value = 1
  await loadCandidates()
}

async function loadCandidates() {
  candidateLoading.value = true
  try {
    const response = await getTaggingPhotoCandidates({
      selection_mode: candidateMode.value,
      status: 'approved',
      search: candidateSearch.value || undefined,
      photo_type: candidatePhotoType.value || undefined,
      skip: (candidatePage.value - 1) * candidatePageSize,
      limit: candidatePageSize,
    })
    candidates.value = response.items
    candidateTotal.value = response.total
  } finally {
    candidateLoading.value = false
  }
}

function togglePhoto(photoId: string) {
  if (selectedSet.value.has(photoId)) {
    selectedPhotoIds.value = selectedPhotoIds.value.filter((id) => id !== photoId)
  } else {
    selectedPhotoIds.value = [...selectedPhotoIds.value, photoId]
  }
}

function selectCurrentPage() {
  const ids = new Set(selectedPhotoIds.value)
  candidates.value.forEach((photo) => ids.add(photo.id))
  selectedPhotoIds.value = [...ids]
  assignAllMatched.value = false
}

function clearSelection() {
  selectedPhotoIds.value = []
  assignAllMatched.value = false
}

async function createBatchTasks() {
  if (!form.title || !form.assignee_ids.length) {
    message.error('请填写任务名称并选择标注学生')
    return
  }
  if (!assignAllMatched.value && !selectedPhotoIds.value.length) {
    message.error('请选择照片，或勾选分派全部匹配照片')
    return
  }
  submitting.value = true
  try {
    await createTaggingTaskBatch({
      title: form.title,
      description: form.description || undefined,
      assignee_ids: form.assignee_ids,
      selection_mode: assignAllMatched.value ? candidateMode.value : 'manual',
      search: assignAllMatched.value ? candidateSearch.value || undefined : undefined,
      photo_type: assignAllMatched.value ? candidatePhotoType.value || undefined : undefined,
      status: 'approved',
      photo_ids: assignAllMatched.value ? [] : selectedPhotoIds.value,
      max_photos: 20000,
    })
    message.success('任务已创建并平均分派')
    showCreate.value = false
    form.title = ''
    form.description = ''
    form.assignee_ids = []
    selectedPhotoIds.value = []
    assignAllMatched.value = true
    await loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function review(row: TaggingTaskItem, approved: boolean, note?: string) {
  try {
    if (approved) await approveTaggingItem(row.id, note)
    else await rejectTaggingItem(row.id, note)
    message.success(approved ? '已通过' : '已驳回')
    showDetail.value = false
    await loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '审核失败')
  }
}

async function batchReview(task: TaggingTask, approved: boolean) {
  const itemIds = selectedSubmittedIds(task)
  if (!itemIds.length) return
  reviewing.value = true
  try {
    const updated = approved
      ? await batchApproveTaggingItems(itemIds)
      : await batchRejectTaggingItems(itemIds)
    checkedRowsByTask[task.id] = []
    message.success(`${approved ? '通过' : '驳回'} ${updated.length} 条待审核标注`)
    await loadData()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '批量审核失败')
  } finally {
    reviewing.value = false
  }
}

function classificationSummary(value: Record<string, any> | null) {
  if (!value) return ''
  return Object.entries(value)
    .map(([key, item]) => `${facetLabel(key, taxonomyFacets.value)}：${classificationValue(key, item)}`)
    .filter((item) => !item.endsWith('：'))
    .join('；')
}

function classificationValue(facetKey: string, value: any): string {
  if (!value) return ''
  const values = Array.isArray(value)
    ? value
    : Array.isArray(value.nodes)
      ? value.nodes
      : Array.isArray(value.node_ids)
        ? value.node_ids
        : [value]
  return values.map((item) => classificationItemLabel(facetKey, item)).filter(Boolean).join('、')
}

function classificationItemLabel(facetKey: string, value: any): string {
  if (typeof value === 'number') return nodePathLabel(facetKey, value)
  if (typeof value === 'string') return value
  const nodeId = value?.node_id || value?.id
  if (nodeId) return value.path?.length ? value.path.join(' / ') : nodePathLabel(facetKey, nodeId) || value.node_name || ''
  if (Array.isArray(value?.path) && value.path.length) return value.path.join(' / ')
  return value?.node_name || value?.name || ''
}

function nodePathLabel(facetKey: string, nodeId: number): string {
  const facet = taxonomyFacets.value.find((item) => item.key === facetKey)
  const node = findTaxonomyNode(facet, nodeId)
  if (!node) return ''
  const optionPath: string[] = []
  let current = node
  while (current) {
    optionPath.unshift(current.name)
    const parentId = current.parent_id
    if (!parentId) break
    const parent = findTaxonomyNode(facet, parentId)
    if (!parent) break
    current = parent
  }
  return optionPath.join(' / ')
}

function sortedText(values: string[]) {
  return [...values].sort().join('、')
}

function tagDiffSummary(original: string[], submitted: string[]) {
  const originalSet = new Set(original)
  const submittedSet = new Set(submitted)
  const added = submitted.filter((tag) => !originalSet.has(tag))
  const removed = original.filter((tag) => !submittedSet.has(tag))
  const parts = [submitted.join('、') || '-']
  if (added.length) parts.push(`新增：${added.join('、')}`)
  if (removed.length) parts.push(`移除：${removed.join('、')}`)
  return parts.join('；')
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待标注',
    in_progress: '进行中',
    reviewing: '审核中',
    submitted: '待审核',
    approved: '已通过',
    rejected: '已驳回',
    completed: '已完成',
  }
  return labels[status] || status
}

function statusType(status: string) {
  const types: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
    submitted: 'warning',
    approved: 'success',
    rejected: 'error',
    pending: 'default',
  }
  return types[status] || 'info'
}
</script>

<style scoped>
.tagging-admin {
  max-width: 1400px;
  margin: 0 auto;
}

.task-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.task-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 108px) minmax(220px, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}

.stat-cell,
.stat-progress {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px;
}

.stat-cell span,
.stat-progress span {
  display: block;
  color: #6b7280;
  font-size: 12px;
  margin-bottom: 4px;
}

.stat-cell strong {
  font-size: 20px;
}

.table-toolbar {
  margin-bottom: 10px;
}

.create-modal {
  width: min(1180px, 92vw);
}

.detail-modal {
  width: min(1120px, 94vw);
}

.detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 440px;
  gap: 16px;
}

.detail-image {
  background: #111827;
  border-radius: 8px;
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.detail-image img {
  max-width: 100%;
  max-height: 680px;
  object-fit: contain;
}

.diff-panel p {
  color: #6b7280;
  margin: 6px 0 0;
}

.changed-value {
  color: #c2410c;
  font-weight: 600;
}

.candidate-toolbar {
  margin-bottom: 12px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 10px;
  min-height: 240px;
}

.photo-tile {
  position: relative;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  background: #f3f4f6;
  cursor: pointer;
}

.photo-tile.selected {
  border-color: #18a058;
}

.photo-tile img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.tile-check {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(255, 255, 255, 0.86);
  border-radius: 4px;
  padding: 2px;
}

.tile-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  font-size: 12px;
}

.tile-meta span,
:deep(.filename-cell) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 960px) {
  .stats-row,
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
